from odoo import models, fields, api, tools  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class Policy(models.Model):
    _name = "policy"
    _description = "Policy List"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    # Attributes
    name = fields.Char(string="Name", required=True, tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    # Relationship Attributes
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["company_id"] = self.env.company.id
        self.clear_caches()
        return super().create(vals_list)

    def write(self, vals):
        # Clear cache before updating records
        self.clear_caches()
        return super().write(vals)

    def unlink(self):
        # Clear cache before deleting records
        self.clear_caches()
        return super().unlink()

    @tools.ormcache("self")
    @api.model
    def get_reserved_words(self):
        """
        Return a frozenset of reserved words (lowercased, stripped).
        This result is cached per-model (key uses 'self').
        """
        # use sudo to avoid permission issues when called from other models
        words = self.sudo().search([("active", "=", True)]).mapped("name")
        normalized = {w.strip().lower() for w in words if w}
        # frozenset is hashable and cheap to return from cache
        return frozenset(normalized)

    # Constrains
    _sql_constraints = [
        (
            "policy_unique_name",
            "UNIQUE(name)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not record.name.strip():
                raise ValidationError(
                    "❌ Error: Name cannot be empty or contain only spaces!"
                )
            if len(record.name) > 100:
                raise ValidationError("❌ Error: Name cannot exceed 100 characters!")
            if any(char in record.name for char in r"@#$%&*<>?/|{}[]\\!+=;:,"):
                raise ValidationError(
                    f"❌ Error: Name cannot contain special characters ({r'@#$%&*<>?/|{}[]\!+=;:,'})!"
                )
            if " " in record.name:
                raise ValidationError("❌ Error: Don't contain spaces!")
