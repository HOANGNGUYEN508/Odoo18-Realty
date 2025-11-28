from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError  # type: ignore


class ResCompany(models.Model):
    _inherit = "res.company"

    # Relationship Attributes
    province_id = fields.Many2one(
        "res.country.state", string="Province/City", ondelete="restrict"
    )
    district_id = fields.Many2one(
        "district",
        string="District/Town",
        domain="[('province_id', '=', province_id)]",
        ondelete="restrict",
    )
    commune_id = fields.Many2one(
        "commune",
        string="Commune",
        domain="[('district_id', '=', district_id)]",
        ondelete="restrict",
    )

    # Constrain
    @api.constrains("province_id", "district_id", "commune_id")
    def _check_location_consistency1(self):
        for record in self:
            if (
                record.district_id
                and record.district_id.province_id != record.province_id
            ):
                raise ValidationError(
                    "❌ District does not match the selected province!"
                )
            if (
                record.commune_id
                and record.commune_id.district_id != record.district_id
            ):
                raise ValidationError(
                    "❌ Commune does not match the selected district!"
                )

    # Onchange
    @api.onchange("province_id")
    def _onchange_province_id(self):
        """Reset district and commune when province changes"""
        for record in self:
            if record.province_id:
                # Check if current district belongs to new province
                if (
                    record.district_id
                    and record.district_id.province_id != record.province_id
                ):
                    record.district_id = False
                # Always reset commune when province changes
                record.commune_id = False
            else:
                # If province is cleared, clear district and commune
                record.district_id = False
                record.commune_id = False

    @api.onchange("district_id")
    def _onchange_district_id(self):
        """Reset commune when district changes"""
        for record in self:
            if record.district_id:
                # Check if current commune belongs to new district
                if (
                    record.commune_id
                    and record.commune_id.district_id != record.district_id
                ):
                    record.commune_id = False
            else:
                # If district is cleared, clear commune
                record.commune_id = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Create config parameter for each new company
        params = self.env["ir.config_parameter"].sudo()
        for record in records:
            key = f"realty_bds.default_job_id_{record.id}"
            # Create the key with empty value
            params.set_param(key, "")

        return records
    
    @api.ondelete(at_uninstall=False)
    def _unlink_default_job_param(self):
        """Delete the associated config parameter when company is deleted"""
        params = self.env['ir.config_parameter'].sudo()
        for record in self:
            key = f'realty_bds.default_job_id_{record.id}'
            # Search and delete the parameter if it exists
            param = params.search([('key', '=', key)], limit=1)
            if param:
                param.unlink()