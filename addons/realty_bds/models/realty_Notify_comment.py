from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore
from odoo.http import request  # type: ignore
from markupsafe import Markup  # type: ignore
import datetime
import logging
import re
import html
import unicodedata
from typing import Optional

_logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")
_ALLOWED_PUNCT = set(".,!?:;\"'`-+()[]{}@#$%&*=/|\\^~<>")


class RealtyComment(models.Model):
    _name = "realty_comment"
    _description = "Comment for notify inheritan models"
    _order = "create_date DESC"
    _parent_name = "parent_id"
    _parent_store = True

    # Attributes
    content = fields.Text(string="Comment", required=True)
    parent_left = fields.Integer(index=True)
    parent_right = fields.Integer(index=True)
    parent_path = fields.Char(index=True)

    # Relationship Attributes
    res_model = fields.Char(
        string="Resource Model",
        index=True,
        required=True,
        help="Model string, e.g. 'notification'",
    )
    res_id = fields.Integer(
        string="Resource ID", index=True, required=True, help="ID in the resource model"
    )
    parent_id = fields.Many2one("realty_comment", string="Reply To", ondelete="cascade")
    child_ids = fields.One2many(
        "realty_comment", "parent_id", string="Replies", copy=False
    )
    like_user_ids = fields.Many2many(
        "res.users", "comment_like_rel", "comment_id", "user_id", string="Liked By"
    )

    # Computed Attributes
    like_count = fields.Integer(
        string="Likes", compute="_compute_like_count", store=True
    )
    is_author = fields.Boolean(
        string="Is Author", compute="_compute_is_author", store=True
    )
    child_count = fields.Integer(
        string="Replies Count", compute="_compute_child_count", store=True
    )
    comment_level = fields.Integer(
        string="Comment Level", default=0
    )  # compute in create to avoid recursion issues

    @api.depends("child_ids")
    def _compute_child_count(self):
        for rec in self:
            rec.child_count = len(rec.child_ids)

    @api.depends("like_user_ids")
    def _compute_like_count(self):
        for rec in self:
            rec.like_count = len(rec.like_user_ids)

    @api.depends("res_model", "res_id", "create_uid")
    def _compute_is_author(self):
        for rec in self:
            rec.is_author = False
            if not rec.res_model or not rec.res_id or not rec.create_uid:
                continue

            try:
                # Safely get the target model and record
                target_model = self.env[rec.res_model]
                target = target_model.sudo().browse(rec.res_id)
                if not target.exists():
                    continue

                # Get the target's owner using a more reliable method
                owner = None
                if hasattr(target, "create_uid"):
                    owner = target.create_uid

                # Check if current user is the owner
                if owner and rec.create_uid.id == owner.id:
                    rec.is_author = True

            except Exception:
                # Handle cases where model doesn't exist or user can't access
                continue

    # Actions
    @api.model
    def action_toggle_like(self, comment_id):
        rec = self.sudo().browse(int(comment_id))
        rec.ensure_one()

        # Check if user has the group
        group_dict = (
            self.env["permission_tracker"]._get_permission_groups(rec.res_model) or {}
        )
        user_group = group_dict.get("user_group")
        realty_group = group_dict.get("realty_group")
        if not (
            self.env.user.has_group(user_group) or self.env.user.has_group(realty_group)
        ):
            raise AccessError(
                "You don't have the necessary permissions to like comment."
            )

        uid = self.env.uid
        currently_liked = uid in rec.like_user_ids.ids
        rec = rec.with_context(skip_custom_realty_write_logic=True)
        rec.sudo().like_user_ids = [(3 if currently_liked else 4, uid)]
        rec._invalidate_cache(["like_user_ids", "like_count"])

        like_payload = {
            "type": "like_toggle",
            "id": rec.id,
            "like_count": rec.like_count or 0,
            "res_model": rec.res_model,
            "res_id": rec.res_id,
        }
        try:
            self._push_bus_notifications([like_payload])
        except Exception:
            _logger.exception(
                "Failed to send like update for realty_comment %s", rec.id
            )

        return {"count": rec.like_count}

    # Helper method
    def _sanitize_content(self, content: Optional[str]) -> str:
        """
        Sanitize comment content while preserving multilingual text and emojis.

        - Escapes HTML to avoid injected tags.
        - Keeps Unicode letters, numbers, most punctuation, symbols and emojis.
        - Removes control characters and unusual symbols.
        - Collapses whitespace to a single space.
        """
        if not content or not isinstance(content, str):
            return content or ""

        # 1) Make HTML-safe first
        s = html.escape(content)

        # 2) Normalize Unicode to a stable form
        s = unicodedata.normalize("NFC", s)

        # 3) Build output by inspecting Unicode categories (very fast)
        out_chars = []
        append = out_chars.append
        for ch in s:
            # keep whitespace as a single space (will be collapsed later)
            if ch.isspace():
                append(" ")
                continue

            cat = unicodedata.category(ch)  # e.g. 'Lu', 'Ll', 'Nd', 'So', 'Cc', ...

            # Allow letters (L*), numbers (N*)
            if cat[0] in ("L", "N"):
                append(ch)
                continue

            # Allow common punctuation/symbol categories and emojis (So)
            if cat in ("Pc", "Pd", "Po", "Ps", "Pe", "Sm", "Sc", "Sk", "So"):
                append(ch)
                continue

            # Allow selected ASCII punctuation not covered above
            if ch in _ALLOWED_PUNCT:
                append(ch)
                continue

            # otherwise: skip character (control chars, private-use, etc.)
            # This removes potentially surprising control / invis chars
            # and any other characters we don't want to allow.
            # (No action needed here.)
            continue

        # 4) Collapse whitespace runs and trim
        sanitized = _WHITESPACE_RE.sub(" ", "".join(out_chars)).strip()

        return sanitized

    def _normalize_for_bus(self, value):
        """Normalize common Odoo/Python objects into JSON-safe primitives."""
        # Record-like (res.users etc.)
        try:
            if hasattr(value, "id") and (
                hasattr(value, "name") or hasattr(value, "display_name")
            ):
                vid = int(value.id) if value.id is not None else None
                vname = (
                    getattr(value, "name", None)
                    or getattr(value, "display_name", None)
                    or ""
                )
                return [vid, str(vname)]
        except Exception:
            pass

        # tuple/list -> normalized list or False for falsy id
        if isinstance(value, (tuple, list)):
            if len(value) >= 2:
                first = value[0]
                if first is False or first is None:
                    return False
                try:
                    return [int(first), str(value[1])]
                except Exception:
                    return [value[0], value[1]]
            return list(value)

        # datetime -> isoformat
        if isinstance(value, (datetime.datetime, datetime.date)):
            try:
                return value.isoformat()
            except Exception:
                return str(value)

        # primitives
        if isinstance(value, (bool, int, float, str)) or value is None:
            return value

        try:
            return str(value)
        except Exception:
            return None

    @api.model
    def _push_bus_notifications(self, payloads):
        """Normalize each payload field and send a single shaped message per item."""
        try:
            bus = self.env["bus.bus"]
        except Exception:
            _logger.info("bus.bus not available; skipping realty_comment push")
            return

        if not isinstance(payloads, (list, tuple)):
            payloads = [payloads]

        for p in payloads:
            try:
                # if p is not a dict, convert to dict form
                if not isinstance(p, dict):
                    _logger.warning(
                        "realty_comment: unexpected payload type %r", type(p)
                    )
                    continue

                normalized = {}
                for k, v in (p or {}).items():
                    try:
                        normalized[k] = self._normalize_for_bus(v)
                    except Exception:
                        normalized[k] = None

                # Send with the fixed notification type
                bus._sendone(
                    f"realty_comment_{normalized.get('res_model')}_{normalized.get('res_id')}",
                    "realty_notify",
                    normalized,
                )
            except Exception:
                _logger.exception(
                    "Failed to send bus message for realty_comment: %r", p
                )

    def _send_removal_notification(
        self, target_partner_id, moderator_name, reason, content, res_model, res_id
    ):
        """Send removal notification to the comment author."""
        if not target_partner_id:
            return
        if not (res_model and res_id):
            return
        rec = self.env[res_model].sudo().browse(int(res_id))
        # Build styled HTML body
        html_body = f"""
            <div style="font-family: Arial, sans-serif; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #ff6b6b;">
                <h3 style="color: #333; margin-top: 0;">Comment Removed</h3>
                <p style="color: #555;">
                    <strong>Moderator {html.escape(moderator_name)}</strong> has removed your comment.
                </p>
                <p style="color: #555; margin-bottom: 10px;">
                    This comment was removed from
                    <strong>{html.escape(str(res_model))}</strong>
                    posted by
                    <strong>{html.escape(str(rec.create_uid.name or ""))}</strong>.
                </p>
                <div style="background: white; padding: 10px; margin: 10px 0; border-radius: 4px;">
                    <strong>Comment:</strong>
                    <blockquote style="margin: 10px 0; padding: 10px; background: #f5f5f5; border-left: 3px solid #ddd;">
                        {html.escape(content or "")}
                    </blockquote>
                </div>
                <p style="color: #555;">
                    <strong>Reason:</strong> <em>{html.escape(reason or "No reason provided")}</em>
                </p>
                <p style="font-size: 0.9em; color: #666; margin-bottom: 0;">
                    If you disagree with this action, please reply or contact the moderator for more details.
                </p>
            </div>
        """

        msg = None

        # Try to post to the record's chatter

        try:
            rec = self.env[res_model].sudo().browse(int(res_id))
            if rec.exists():
                try:
                    msg = rec.sudo().message_post(
                        body=Markup(html_body),
                        subject="Comment Removal Notification",
                        subtype_xmlid="mail.mt_note",
                    )
                except Exception as e:
                    _logger.warning("message_post failed: %s", e)
                    msg = None
        except Exception as e:
            _logger.warning("Failed to get target record: %s", e)

        # Fallback: create mail.message directly
        if not msg:
            msg_vals = {
                "model": res_model or self._name,
                "res_id": int(res_id) if res_id else False,
                "body": Markup(html_body),
                "subject": "Comment Removal Notification",
                "message_type": "notification",
                "partner_ids": [(4, target_partner_id)],
            }

            try:
                msg = self.env["mail.message"].sudo().create(msg_vals)
            except Exception as e:
                _logger.error("Failed to create mail.message: %s", e)
                return

        # Ensure notification exists and is unread
        if msg and msg.exists():
            self.env["mail.notification"].sudo().create(
                {
                    "res_partner_id": target_partner_id,
                    "notification_type": "inbox",
                    "mail_message_id": msg.id,
                    "is_read": False,
                }
            )

    # Model Method
    @api.model
    def get_top_level_page(self, res_model, res_id, limit=10, offset=0):
        """Return a page of top-level comments (with total_count for paging)."""
        try:
            res_id = int(res_id)
        except Exception:
            return {"comments": [], "hasMore": False, "page": 0, "total_count": 0}

        domain = [
            ("res_model", "=", res_model),
            ("res_id", "=", res_id),
            ("parent_id", "=", False),
        ]

        total_count = self.search_count(domain)

        comments = self.search(
            domain,
            limit=int(limit),
            offset=int(offset),
            order="like_count DESC, create_date DESC",
        )

        data = comments.read(
            [
                "id",
                "content",
                "create_uid",
                "create_date",
                "like_count",
                "child_count",
                "res_model",
                "res_id",
            ]
        )

        return {
            "comments": data,
            "hasMore": len(comments) == int(limit),
            "page": (int(offset) // int(limit)),
            "total_count": int(total_count),
        }

    @api.model
    def get_replies_page(self, comment_id, limit=5, offset=0):
        """Get paginated replies for a comment"""
        comment = self.browse(comment_id)
        if not comment.exists():
            return {"replies": [], "hasMore": False, "page": 0}

        replies = self.search(
            [("parent_id", "=", comment_id)],
            limit=limit,
            offset=offset,
            order="like_count DESC, create_date DESC",
        )

        return {
            "replies": replies.read(
                [
                    "id",
                    "content",
                    "create_uid",
                    "create_date",
                    "like_count",
                    "child_count",
                    "comment_level",
                ]
            ),
            "hasMore": len(replies) == limit,
            "page": offset // limit,
        }

    @api.model_create_multi
    def create(self, vals_list):
        if not isinstance(vals_list, list) or len(vals_list) == 0:
            raise ValidationError("No values provided for comment creation.")
        if len(vals_list) > 1:
            raise ValidationError(
                "Only single comment creation is allowed in this API."
            )

        # Extract client_tmp_id from context for deduplication
        ctx = dict(self.env.context or {})
        client_tmp_id = ctx.get("client_tmp_id")
        create_or_reply = ctx.get("create_or_reply")
        if not client_tmp_id or not create_or_reply:
            raise ValidationError("Context is required.")

        # normalize single vals dict
        vals = dict(vals_list[0])

        required_keys = {"res_model", "res_id", "content"}
        if create_or_reply == "reply":
            required_keys.add("parent_id")
        missing = [k for k in required_keys if k not in vals]
        if missing:
            raise ValidationError(
                f"Missing required keys on create: {', '.join(missing)}"
            )
        post = self.env[vals["res_model"]].browse(vals["res_id"]).exists()
        if not post:
            raise UserError(
                "The post you comment to no longer exists (deleted by another user)."
            )
        if not vals.get("res_model") or not vals.get("res_id"):
            raise ValidationError(
                "res_model and res_id are required to create a comment."
            )

        vals["content"] = self._sanitize_content(vals.get("content"))

        parent_id = vals.get("parent_id")
        if parent_id:
            parent_rec = self.browse(parent_id)
            if parent_rec.exists():
                if not vals.get("res_model"):
                    vals["res_model"] = parent_rec.res_model
                if not vals.get("res_id"):
                    vals["res_id"] = parent_rec.res_id

        # compute comment_level
        if vals.get("parent_id"):
            parent = self.browse(vals["parent_id"])
            vals["comment_level"] = (parent.comment_level or 0) + 1
        else:
            vals["comment_level"] = 0

        # create (use super with a list as required)
        recs = super().create([vals])
        if not recs:
            return recs
        rec = recs[0]
        post.compute_comment_count(True)
        # Prepare payloads: create payload + optional parent_update (coalesced)
        try:
            create_payload = {
                "type": "create",
                "id": rec.id,
                "content": rec.content,
                "create_uid": rec.create_uid
                and (rec.create_uid.id, rec.create_uid.name)
                or False,
                "create_date": rec.create_date,
                "like_count": rec.like_count or 0,
                "child_count": rec.child_count or 0,
                "res_model": rec.res_model,
                "res_id": rec.res_id,
                "parent_id": rec.parent_id.id if rec.parent_id else False,
                "client_tmp_id": client_tmp_id,
            }

            payloads = [create_payload]

            # coalesce parent update if parent exists (send in same batch)
            if rec.parent_id:
                parent = rec.parent_id
                parent_payload = {
                    "type": "parent_update",
                    "id": parent.id,
                    "child_count": parent.child_count or 0,
                    "res_model": parent.res_model,
                    "res_id": parent.res_id,
                }
                payloads.append(parent_payload)

            # push notifications (best-effort)
            self._push_bus_notifications(payloads)

        except Exception:
            _logger.exception(
                "Failed to prepare/send bus notifications for created realty_comment %s",
                rec.id,
            )

        return recs

    def write(self, vals):
        self.ensure_one()
        if self.env.context.get("skip_custom_realty_write_logic"):
            return super(RealtyComment, self).write(vals)
        content_only = set(vals.keys()) == {"content"} and "content" in vals
        if not content_only:
            raise UserError("Only content field can be updated.")
        vals["content"] = self._sanitize_content(vals.get("content"))
        result = super(RealtyComment, self).write(vals)

        if result:
            rec = self.browse(self.id)  # reload to get updated values
            update_payload = {
                "type": "update",
                "id": rec.id,
                "content": rec.content,
                "write_date": rec.write_date,
                "res_model": rec.res_model,
                "res_id": rec.res_id,
            }
            try:
                self._push_bus_notifications(update_payload)
            except Exception:
                _logger.exception(
                    "Failed to send update payload for realty_comment %s", rec.id
                )

            return {
                "id": rec.id,
                "content": rec.content,
                "write_date": rec.write_date,
            }
        else:
            return {"id": False}

    def unlink(self, reason=None):
        if self.env.context.get("skip_realty_delete_custom"):
            # Delete in bulk only happen if user delete the post
            return super(RealtyComment, self).unlink()
        self.ensure_one()
        is_owner = self.create_uid.id == self.env.uid

        if reason is None:
            reason_str = None
        else:
            reason_str = (
                str(reason).strip() if isinstance(reason, str) else str(reason).strip()
            )

        if is_owner:
            if reason_str:
                raise UserError(
                    "Why do you need to provide reason to delete your own comment?"
                )
        elif not reason_str:
            raise ValidationError("Moderator removal requires a reason.")
        target = (
            self.create_uid.partner_id.id
            if self.create_uid and self.create_uid.partner_id
            else None
        )
        parent_id = self.parent_id.id if self.parent_id else False
        rec_res_model = self.res_model
        rec_res_id = self.res_id
        post = self.env[rec_res_model].browse(rec_res_id).exists()
        if not post:
            raise UserError(
                "The post you comment to no longer exists (deleted by another user)."
            )
        deleted_id = self.id
        content = self.content
        result = super(RealtyComment, self).unlink()
        if result:
            delete_payload = {
                "type": "delete",
                "id": deleted_id,
                "parent_id": parent_id,
                "res_model": rec_res_model,
                "res_id": rec_res_id,
            }
            payloads = [delete_payload]

            if parent_id:
                # reload parent to reflect updated child_count after deletion
                parent = self.browse(parent_id)
                parent_payload = {
                    "type": "parent_update",
                    "id": parent.id,
                    "child_count": parent.child_count or 0,
                    "res_model": parent.res_model,
                    "res_id": parent.res_id,
                }
                payloads.append(parent_payload)

            try:
                self._push_bus_notifications(payloads)
            except Exception:
                _logger.exception(
                    "Failed to send delete/parent_update for realty_comment %s",
                    deleted_id,
                )
            if not is_owner:
                self._send_removal_notification(
                    target,
                    self.env.user.name,
                    reason_str,
                    content,
                    rec_res_model,
                    rec_res_id,
                )
            post.compute_comment_count(False)
            return {"deleted_id": deleted_id, "parent_id": parent_id}
        else:
            return {"deleted_id": False, "parent_id": False}

    # Constrain
    @api.constrains("content")
    def _check_content(self):
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )
        for record in self:
            clean_content = record.content.strip().lower() if record.content else ""
            if not clean_content:
                raise ValidationError("Comment cannot be empty!")
            match = next((w for w in reserved_words if w in clean_content), None)
            if match:
                raise ValidationError(
                    f"❌ Error: Name contains reserved word: '{match}'!"
                )
            if len(record.content) > 500:
                raise ValidationError("Comment cannot exceed 500 characters!")

    @api.constrains("res_model", "res_id")
    def _check_target_exists(self):
        for rec in self:
            try:
                model = self.env[rec.res_model]
                if not model.sudo().browse(rec.res_id).exists():
                    raise ValidationError(
                        f"Target record not found: {rec.res_model} (id={rec.res_id})."
                    )
            except KeyError:
                raise ValidationError(f"Model '{rec.res_model}' does not exist.")

    @api.constrains("parent_id", "res_model", "res_id")
    def _check_parent_same_target(self):
        for rec in self:
            if rec.parent_id:
                parent = rec.parent_id
                if parent.res_model != rec.res_model or parent.res_id != rec.res_id:
                    raise ValidationError(
                        "Reply must belong to the same source record as its parent comment."
                    )

    def init(self):
        # call super, but log any exception
        try:
            super(RealtyComment, self).init()
        except Exception:
            _logger.exception("super().init() failed during module init — continuing")

        cr = self.env.cr
        try:
            cr.execute(
                """
                CREATE INDEX IF NOT EXISTS realty_comment_res_model_res_id_idx
                ON realty_comment (res_model, res_id)
            """
            )
        except Exception:
            _logger.exception(
                "Failed to create index realty_comment_res_model_res_id_idx"
            )

        try:
            cr.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS comment_like_rel_unique_idx
                ON comment_like_rel (comment_id, user_id)
            """
            )
        except Exception:
            _logger.exception(
                "Failed to create unique index comment_like_rel_unique_idx"
            )
