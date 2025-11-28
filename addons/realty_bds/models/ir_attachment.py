from odoo import models, fields, api  # type: ignore
from odoo.exceptions import AccessError  # type: ignore


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # who it was orphaned from (original owner info)
    orphaned_date = fields.Datetime(string="Orphaned Date", readonly=True)
    orphaned_from_model = fields.Char(string="Orphaned From Model", readonly=True)
    orphaned_from_res_id = fields.Integer(
        string="Orphaned From Record ID",
        readonly=True,
        default=-1,
        help="-1: Draft record, 0: Orphaned, >0: Original record ID",
    )

    @api.model
    def mark_orphaned(self, ids, from_model=None, from_res_id=None):
        """
        Mark attachments as orphaned.
        :param ids: list of attachment ids (e.g., [1, 2, 3])
        :param from_model: original model name (e.g., 'notification')
        :param from_res_id: original record id
        :return: True on success
        """
        if not ids:
            return True

        attachments = self.browse(ids)
        current_uid = self.env.uid

        writable_attachments = self.env["ir.attachment"]
        creator_attachments = self.env["ir.attachment"]

        for att in attachments:
            try:
                att.check_access("write")
                writable_attachments += att
            except AccessError:
                if att.create_uid.id == current_uid:
                    creator_attachments += att
                else:
                    raise AccessError(
                        "You are not allowed to mark attachment %s as orphaned.", att.id
                    )

        orphan_vals = {
            "orphaned_date": fields.Datetime.now(),
            "orphaned_from_model": from_model or "",
            "orphaned_from_res_id": from_res_id or 0,
            "res_id": 0,
            "res_model": "",
        }

        if writable_attachments:
            writable_attachments.write(orphan_vals)

        if creator_attachments:
            creator_attachments.sudo().write(orphan_vals)

        return True

    @api.model
    def mark_true(self, ids):
        """
        INTERNAL: Mark attachments as saved (bypasses security)
        Only call from trusted server-side code
        """
        if not ids:
            return True
        if not isinstance(ids, list):
            ids = [ids]
        valid_ids = [att_id for att_id in ids if isinstance(att_id, int) and att_id > 0]
        if not valid_ids:
            return True

        attachments = self.sudo().browse(valid_ids)
        if attachments:
            attachments.write({"orphaned_from_res_id": 0})
