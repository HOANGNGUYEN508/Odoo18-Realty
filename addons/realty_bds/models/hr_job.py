from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class JobTitle(models.Model):
    _inherit = "hr.job"
    _description = "Job Title"
    _order = "name asc"

    # Relationship Attributes
    implied_ids = fields.Many2many(
        "res.groups",
        "hr_job_group_rel",
        "hr_job_id",
        "group_id",
        string="Rights group are assigned",
    )

    # Model Method
    def write(self, vals):
        # Call the parent write method to update the record
        res = super(JobTitle, self).write(vals)
        # Check if implied_ids is being updated
        if "implied_ids" in vals:
            # Find all users associated with this job title
            users = self.env["res.users"].search([("hr_job_id", "in", self.ids)])
            if users:
                # Sync groups for all affected users
                users._sync_groups_from_job_title()
        return res

    # Constrains
    _sql_constraints = [
        ("name_unique", "unique(name)", "This name already exists!"),
    ]

    @api.constrains("name")
    def _check_name(self):
        reserved_words = []
        try:
            reserved_words = request.env["policy"].sudo().search([]).mapped("name")
        except KeyError:
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )
        reserved_words = set(
            word.strip().lower() for word in reserved_words
        )  # Normalize
        for record in self:
            clean_name = (
                record.name.strip().lower()
            )  # Convert to lowercase to check correctly
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Name cannot be empty or contain only spaces!"
                )
            if len(record.name) > 100:  # Limit name length
                raise ValidationError("❌ Error: Name cannot exceed 100 characters!")
            if any(
                char in record.name for char in r"@#$%&*<>?/|{}[]\\!+=;:,"
            ):  # Block special characters
                raise ValidationError(
                    "❌ Error: Name cannot contain special characters!"
                )
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(f"❌ Error: Name '{record.name}' is not allowed!")
