from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore
from odoo.http import request  # type: ignore
import datetime
import logging

_logger = logging.getLogger(__name__)


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
    res_id = fields.Integer(string="Resource ID",
                            index=True,
                            required=True,
                            help="ID in the resource model")
    parent_id = fields.Many2one("realty_comment",
                                string="Reply To",
                                ondelete="cascade")
    child_ids = fields.One2many("realty_comment",
                                "parent_id",
                                string="Replies",
                                copy=False)
    like_user_ids = fields.Many2many("res.users",
                                     "comment_like_rel",
                                     "comment_id",
                                     "user_id",
                                     string="Liked By")

    # Computed Attributes
    like_count = fields.Integer(string="Likes",
                                compute="_compute_like_count",
                                store=True)
    is_author = fields.Boolean(string="Is Author",
                               compute="_compute_is_author",
                               store=True)
    child_count = fields.Integer(string="Replies",
                                 compute="_compute_child_count",
                                 store=True)
    comment_level = fields.Integer(
        string="Comment Level",
        default=0)  # compute in create to avoid recursion issues

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
        group_dict = self.env["permission_tracker"]._get_permission_groups(
            rec.res_model) or {}
        user_group = group_dict.get("user_group")
        realty_group = group_dict.get("realty_group")
        if not (self.env.user.has_group(user_group)
                or self.env.user.has_group(realty_group)):
            raise AccessError(
                "You don't have the necessary permissions to like comment.")

        uid = self.env.uid
        currently_liked = uid in rec.like_user_ids.ids
        rec = rec.with_context(skip_custom_realty_write_logic=True)
        rec.sudo().like_user_ids = [(3 if currently_liked else 4, uid)]
        rec._invalidate_cache(["like_user_ids", "like_count"])

        like_payload = {
            "type":
            "like_toggle",
            "id":
            rec.id,
            "like_count":
            rec.like_count or 0,
            "res_model":
            rec.res_model,
            "res_id":
            rec.res_id,
        }
        try:
            self._push_bus_notifications([like_payload])
        except Exception:
            _logger.exception(
                "Failed to send like update for realty_comment %s", rec.id)

        return {"count": rec.like_count }

    # Helper method
    def _normalize_for_bus(self, value):
        """Normalize common Odoo/Python objects into JSON-safe primitives."""
        # Record-like (res.users etc.)
        try:
            if hasattr(value, "id") and (hasattr(value, "name")
                                         or hasattr(value, "display_name")):
                vid = int(value.id) if value.id is not None else None
                vname = (getattr(value, "name", None)
                         or getattr(value, "display_name", None) or "")
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
                        "realty_comment: unexpected payload type %r", type(p))
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
                    "Failed to send bus message for realty_comment: %r", p)

    # Model Method
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
            order="like_count DESC, create_date ASC",
        )

        return {
            "replies":
            replies.read([
                "id",
                "content",
                "create_uid",
                "create_date",
                "like_count",
                "child_count",
                "comment_level",
            ]),
            "hasMore":
            len(replies) == limit,
            "page":
            offset // limit,
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        if not isinstance(vals_list, list) or len(vals_list) == 0:
            raise ValidationError("No values provided for comment creation.")
        if len(vals_list) > 1:
            raise ValidationError(
                "Only single comment creation is allowed in this API.")

        # Extract client_tmp_id from context for deduplication
        ctx = dict(self.env.context or {})
        client_tmp_id = ctx.get("client_tmp_id")

        # normalize single vals dict
        vals = dict(vals_list[0])
        ctx = dict(self.env.context or {})
        
        if not vals.get("res_model") or not vals.get("res_id"):
            raise ValidationError("res_model and res_id are required to create a comment.")

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

        # Prepare payloads: create payload + optional parent_update (coalesced)
        try:
            create_payload = {
                "type":
                "create",
                "id":
                rec.id,
                "content":
                rec.content,
                "create_uid":
                rec.create_uid and (rec.create_uid.id, rec.create_uid.name)
                or False,
                "create_date":
                rec.create_date,
                "like_count":
                rec.like_count or 0,
                "child_count":
                rec.child_count or 0,
                "res_model":
                rec.res_model,
                "res_id":
                rec.res_id,
                "parent_id":
                rec.parent_id.id if rec.parent_id else False,
                "client_tmp_id":
                client_tmp_id,
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
        if self.env.context.get('skip_custom_realty_write_logic'):
            return super(RealtyComment, self).write(vals)
        content_only = set(vals.keys()) == {'content'} and 'content' in vals
        if not content_only:
            raise UserError("Only content field can be updated.")
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
                self._push_bus_notifications([update_payload])
            except Exception:
                _logger.exception("Failed to send update payload for realty_comment %s", rec.id)

            return {
                "id":
                rec.id,
                "content":
                rec.content,
                "write_date":
                rec.write_date,
            }
        else: return { "id": False }

    def unlink(self):
        self.ensure_one()
        parent_id = self.parent_id.id if self.parent_id else False
        rec_res_model = self.res_model
        rec_res_id = self.res_id
        deleted_id = self.id
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
            return {"deleted_id": deleted_id, "parent_id": parent_id}
        else: return {"deleted_id": False, "parent_id": False}

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
            clean_content = record.content.strip().lower(
            ) if record.content else ""
            if not clean_content:
                raise ValidationError("Comment cannot be empty!")
            match = next((w for w in reserved_words if w in clean_content),
                         None)
            if match:
                raise ValidationError(
                    f"❌ Error: Name contains reserved word: '{match}'!")
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
                raise ValidationError(
                    f"Model '{rec.res_model}' does not exist.")

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
            _logger.exception(
                "super().init() failed during module init — continuing")

        cr = self.env.cr
        try:
            cr.execute("""
                CREATE INDEX IF NOT EXISTS realty_comment_res_model_res_id_idx
                ON realty_comment (res_model, res_id)
            """)
        except Exception:
            _logger.exception(
                "Failed to create index realty_comment_res_model_res_id_idx")

        try:
            cr.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS comment_like_rel_unique_idx
                ON comment_like_rel (comment_id, user_id)
            """)
        except Exception:
            _logger.exception(
                "Failed to create unique index comment_like_rel_unique_idx")
