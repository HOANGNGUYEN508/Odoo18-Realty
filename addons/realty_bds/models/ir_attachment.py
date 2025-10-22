from odoo import models, fields, api  # type: ignore
from odoo.exceptions import AccessError  # type: ignore

class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    # who it was orphaned from (original owner info)
    orphaned_date = fields.Datetime(string="Orphaned Date", readonly=True)
    orphaned_from_model = fields.Char(string="Orphaned From Model", readonly=True)
    orphaned_from_res_id = fields.Integer(string="Orphaned From Record ID", readonly=True)

    @api.model
    def mark_orphaned(self, ids, from_model=None, from_res_id=None):
        """
        Mark attachments as orphaned.
        ids: list of attachment ids
        from_model: string (e.g. 'notification')
        from_res_id: int (original record id) or falsy
        Returns True on success or raises AccessError when not allowed.
        """
        if not ids:
            return False
        attachments = self.browse(ids)
        for att in attachments:
            # Try to check write access first
            try:
                att.check_access("write")
                # current user has write permissions -> use normal write
                att.write({
                    "orphaned_date": fields.Datetime.now(),
                    "orphaned_from_model": from_model or "",
                    "orphaned_from_res_id": int(from_res_id) if from_res_id else 0,
                })
            except AccessError:
                # If user created the attachment, allow them to mark it orphaned
                if att.create_uid and att.create_uid.id == self.env.uid:
                    # persist regardless of attachment access rules (uploader intent)
                    att.sudo().write({
                        "orphaned_date": fields.Datetime.now(),
                        "orphaned_from_model": from_model or "",
                        "orphaned_from_res_id": int(from_res_id) if from_res_id else 0,
                    })
                else:
                    raise AccessError("You are not allowed to mark this attachment as orphaned.")
        return True