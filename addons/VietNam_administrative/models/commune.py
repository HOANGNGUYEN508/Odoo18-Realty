from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore


class Commune(models.Model):
    _name = "commune"
    _description = "Commune"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name asc"

    # Attributes
    active = fields.Boolean(string="Active", default=True, tracking=True)
    name = fields.Char(string="Commune", tracking=True, required=True)

    # Relationship Attributes
    province_id = fields.Many2one(
        "res.country.state",
        string="Province/City",
        required=True,
        domain="[('country_id.code', '=', 'VN')]",
        tracking=True,
    )
    district_id = fields.Many2one(
        "district",
        string="District/Town",
        required=True,
        domain="[('province_id', '=', province_id)]",
        tracking=True,
    )

    # Constrain
    _sql_constraints = [
        (
            "commune_unique_name",
            "UNIQUE(name,district_id,province_id)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]

    @api.constrains("district_id", "province_id")
    def _check_district_province(self):
        for record in self:
            if not record.province_id:
                raise ValidationError("No province/city selected!")
            if (
                record.district_id
                and record.province_id
                and record.district_id.province_id != record.province_id
            ):
                raise ValidationError(
                    f"❌ Error: District '{record.district_id.name}' does not belong to province '{record.province_id.name}'!"
                )

    # Onchange
    @api.onchange("province_id")
    def _onchange_province_id(self):
        # When selecting/editing a province, clear the district if invalid and apply domain
        if self.province_id:
            if self.district_id and self.district_id.province_id != self.province_id:
                self.district_id = False
            return {
                "domain": {"district_id": [("province_id", "=", self.province_id.id)]}
            }
        else:
            self.district_id = False
        return {
            "domain": {
                "district_id": (
                    [("province_id", "=", self.province_id.id)]
                    if self.province_id
                    else []
                )
            }
        }  # Do not display districts if no province is selected
