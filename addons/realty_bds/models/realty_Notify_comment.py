from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError  # type: ignore
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
        string="Replies", compute="_compute_child_count", store=True
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
        uid = self.env.uid
        if uid in rec.like_user_ids.ids:
            rec.sudo().write({"like_user_ids": [(3, uid)]})
            liked = False
        else:
            rec.sudo().write({"like_user_ids": [(4, uid)]})
            liked = True
        rec._invalidate_cache(["like_user_ids", "like_count"])

        update_payload = {
            "type": "update",
            "id": rec.id,
            "create_uid": rec.create_uid
            and (rec.create_uid.id, rec.create_uid.name)
            or False,
            "like_count": rec.like_count or 0,
            "child_count": rec.child_count or 0,
            "res_model": rec.res_model,
            "res_id": rec.res_id,
            "parent_id": rec.parent_id.id if rec.parent_id else False,
        }
        try:
            self._push_bus_notifications([update_payload])
        except Exception:
            _logger.exception(
                "Failed to send like update for realty_comment %s", rec.id
            )

        return {"count": rec.like_count, "liked": liked}

    @api.model
    def action_edit_comment(self, comment_id, new_content):
        rec = self.browse(int(comment_id))
        if not rec.exists():
            raise ValidationError("Comment not found.")
        rec.write({"content": new_content})
        # reload the rec to ensure values updated for the response
        rec = self.browse(rec.id)
        update_payload = {
            "type": "update",
            "id": rec.id,
            "create_uid": rec.create_uid
            and (rec.create_uid.id, rec.create_uid.name)
            or False,
            "content": rec.content,
            "write_date": rec.write_date,
            "like_count": rec.like_count or 0,
            "child_count": rec.child_count or 0,
            "res_model": rec.res_model,
            "res_id": rec.res_id,
            "parent_id": rec.parent_id.id if rec.parent_id else False,
        }
        try:
            self._push_bus_notifications([update_payload])
        except Exception:
            _logger.exception(
                "Failed to send update payload for realty_comment %s", rec.id
            )

        return {
            "id": rec.id,
            "content": rec.content,
            "like_count": rec.like_count,
            "child_count": rec.child_count,
            "create_uid": rec.create_uid
            and (rec.create_uid.id, rec.create_uid.name)
            or False,
            "write_date": rec.write_date,
        }

    @api.model
    def action_delete_comment(self, comment_id):
        rec = self.browse(int(comment_id))
        if not rec.exists():
            raise ValidationError("Comment not found.")

        # capture metadata before unlink
        parent_id = rec.parent_id.id if rec.parent_id else False
        rec_res_model = rec.res_model
        rec_res_id = rec.res_id
        deleted_id = rec.id

        rec.unlink()

        # prepare payloads: delete + optional parent_update
        try:
            delete_payload = {
                "type": "delete",
                "id": deleted_id,
                "parent_id": parent_id,
                "res_model": rec_res_model,
                "res_id": rec_res_id,
            }
            payloads = [delete_payload]

            if parent_id:
                parent = self.browse(parent_id)
                parent_payload = {
                    "type": "parent_update",
                    "id": parent.id,
                    "child_count": parent.child_count or 0,
                    "res_model": parent.res_model,
                    "res_id": parent.res_id,
                }
                payloads.append(parent_payload)

            self._push_bus_notifications(payloads)
        except Exception:
            _logger.exception(
                "Failed to send delete/parent_update for realty_comment %s", deleted_id
            )

        return {"deleted_id": deleted_id}

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
            order="create_date DESC",
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

    # Helper method
    def _raise_if_cant_modify(self):
        """Raise AccessError if current env.user may not modify these records.
        Allowed if owner (create_uid) or admin group (base.group_system)."""
        for rec in self:
            is_owner = rec.create_uid and rec.create_uid.id == self.env.uid
            is_admin = self.env.user.has_group("base.group_system")
            if not (is_owner or is_admin):
                raise AccessError("You don't have permission to modify this comment.")

    def _normalize_for_bus(self, value):
        """Normalize common Odoo/Python objects into JSON-safe primitives."""
        # Record-like (res.users etc.)
        try:
            if hasattr(value, "id") and (hasattr(value, "name") or hasattr(value, "display_name")):
                vid = int(value.id) if value.id is not None else None
                vname = getattr(value, "name", None) or getattr(value, "display_name", None) or ""
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
                    _logger.warning("realty_comment: unexpected payload type %r", type(p))
                    continue

                normalized = {}
                for k, v in (p or {}).items():
                    try:
                        normalized[k] = self._normalize_for_bus(v)
                    except Exception:
                        normalized[k] = None

                # Send with the fixed notification type
                bus._sendone(f"realty_comment_{normalized.get('res_model')}_{normalized.get('res_id')}", "realty_notify", normalized)
            except Exception:
                _logger.exception("Failed to send bus message for realty_comment: %r", p)


    # Model Method
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
        client_tmp_id = ctx.get('client_tmp_id')

        # normalize single vals dict
        vals = dict(vals_list[0])
        ctx = dict(self.env.context or {})

        parent_id = vals.get("parent_id")
        if parent_id:
            parent_rec = self.browse(parent_id)
            if parent_rec.exists():
                if not vals.get("res_model"):
                    vals["res_model"] = parent_rec.res_model
                if not vals.get("res_id"):
                    vals["res_id"] = parent_rec.res_id

        if not vals.get("res_model") and ctx.get("default_res_model"):
            vals["res_model"] = ctx.get("default_res_model")
        if not vals.get("res_id") and ctx.get("default_res_id"):
            try:
                vals["res_id"] = int(ctx.get("default_res_id") or 0)
            except Exception:
                vals["res_id"] = 0

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
        self._raise_if_cant_modify()
        return super(RealtyComment, self).write(vals)

    def unlink(self):
        self.ensure_one()
        self._raise_if_cant_modify()
        return super(RealtyComment, self).unlink()

    # Constrain
    @api.constrains("content")
    def _check_content(self):
        for record in self:
            if not record.content or not record.content.strip():
                raise ValidationError("Comment cannot be empty!")
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
            _logger.exception("Failed to create index realty_comment_res_model_res_id_idx")

        try:
            cr.execute(
            """
                CREATE UNIQUE INDEX IF NOT EXISTS comment_like_rel_unique_idx
                ON comment_like_rel (comment_id, user_id)
            """
            )
        except Exception:
            _logger.exception("Failed to create unique index comment_like_rel_unique_idx")
