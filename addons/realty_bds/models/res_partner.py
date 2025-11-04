from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError  # type: ignore


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Attributes
    citizen_id = fields.Char(string="Số CCCD", tracking=True)
    password = fields.Char(string="Password", tracking=True)

    # Relationship Attributes
    province_id = fields.Many2one(
        "res.country.state", string="Province/City", ondelete="restrict", tracking=True
    )
    district_id = fields.Many2one(
        "district",
        string="District/Town",
        domain="[('province_id', '=', province_id)]",
        ondelete="restrict",
        tracking=True,
    )
    commune_id = fields.Many2one(
        "commune",
        string="Commune",
        domain="[('district_id', '=', district_id)]",
        ondelete="restrict",
        tracking=True,
    )
    province_resident_id = fields.Many2one(
        "res.country.state",
        string="Residence Province/City ",
        ondelete="restrict",
        tracking=True,
    )
    district_resident_id = fields.Many2one(
        "district",
        string="Residence District/Town",
        domain="[('province_id', '=', province_resident_id)]",
        ondelete="restrict",
        tracking=True,
    )
    commune_resident_id = fields.Many2one(
        "commune",
        string="Residence Commune",
        domain="[('district_id', '=', district_resident_id)]",
        ondelete="restrict",
        tracking=True,
    )
    subscribed_partner_ids = fields.Many2many(
        comodel_name='res.partner',
        relation='partner_subscribe_rel',
        column1='partner_id',
        column2='subscribed_partner_id',
        string='Subscribed Partners'
    )

    # Constrains
    _sql_constraints = [
        ("citizen_id_unique", "unique(citizen_id)", "Citizen ID must be unique!"),
    ]

    @api.constrains("citizen_id")
    def _check_citizen_id(self):
        for record in self:
            if record.is_company or not record.user_ids:
                continue
            if not record.citizen_id:
                raise ValidationError(
                    "❌ Citizen ID number is required for individuals!"
                )
            citizen_id = record.citizen_id.strip()
            if not citizen_id.isdigit():
                raise ValidationError("❌ Citizen ID must contain numbers only!")
            if len(citizen_id) != 12:
                raise ValidationError("❌ Citizen ID must be exactly 12 digits!")

    @api.constrains("province_id", "district_id", "commune_id")
    def _check_location_consistency1(self):
        for record in self:
            if (
                record.is_company or not record.user_ids
            ):  # Ignore companies or partners not linked to any user
                continue
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

    @api.constrains(
        "province_resident_id", "district_resident_id", "commune_resident_id"
    )
    def _check_location_consistency2(self):
        for record in self:
            if (
                record.is_company or not record.user_ids
            ):  # Ignore companies or partners not linked to any user
                continue
            if (
                record.district_resident_id
                and record.district_resident_id.province_id
                != record.province_resident_id
            ):
                raise ValidationError(
                    "❌ District does not match the selected province!"
                )
            if (
                record.commune_resident_id
                and record.commune_resident_id.district_id
                != record.district_resident_id
            ):
                raise ValidationError(
                    "❌ Commune does not match the selected district!"
                )

    # Onchange
    @api.onchange('province_id')
    def _onchange_province_id(self):
        """Reset district and commune when province changes"""
        for record in self:
            if record.province_id:
                # Check if current district belongs to new province
                if record.district_id and record.district_id.province_id != record.province_id:
                    record.district_id = False
                # Always reset commune when province changes
                record.commune_id = False
            else:
                # If province is cleared, clear district and commune
                record.district_id = False
                record.commune_id = False

    @api.onchange('district_id')
    def _onchange_district_id(self):
        """Reset commune when district changes"""
        for record in self:
            if record.district_id:
                # Check if current commune belongs to new district
                if record.commune_id and record.commune_id.district_id != record.district_id:
                    record.commune_id = False
            else:
                # If district is cleared, clear commune
                record.commune_id = False

    @api.onchange('province_resident_id')
    def _onchange_province_resident_id(self):
        """Reset resident district and commune when resident province changes"""
        for record in self:
            if record.province_resident_id:
                # Check if current resident district belongs to new resident province
                if (record.district_resident_id and 
                    record.district_resident_id.province_id != record.province_resident_id):
                    record.district_resident_id = False
                # Always reset resident commune when resident province changes
                record.commune_resident_id = False
            else:
                # If resident province is cleared, clear resident district and commune
                record.district_resident_id = False
                record.commune_resident_id = False

    @api.onchange('district_resident_id')
    def _onchange_district_resident_id(self):
        """Reset resident commune when resident district changes"""
        for record in self:
            if record.district_resident_id:
                # Check if current resident commune belongs to new resident district
                if (record.commune_resident_id and 
                    record.commune_resident_id.district_id != record.district_resident_id):
                    record.commune_resident_id = False
            else:
                # If resident district is cleared, clear resident commune
                record.commune_resident_id = False

    # Action
    def action_toggle_subscribe(self, target_partner):
        """Toggle subscription of `self` to `target_partner` (add/remove)."""
        self.ensure_one()
        self.sudo().subscribed_partner_ids = [
            (3 if target_partner in self.subscribed_partner_id.ids else 4, target_partner)
        ]

    def action_notify_admin_new_partner(self, partner):
        """Notify users with 'realty_bds.access_group_full_users' access when a new partner is created"""
        group_xml_id = "realty_bds.access_group_full_users"
        group = self.env.ref(group_xml_id)
        users_to_notify = self.env["res.users"].search(
            [("groups_id", "in", [group.id])]
        )
        if not users_to_notify:
            return
        partner_link = f'<a href="/web#id={partner.id}&model=res.partner&view_type=form">{partner.name}</a>'
        message_body = f"Account: {partner_link}. Pass or Delete."
        for user in users_to_notify:
            if not user.partner_id:
                continue
            channel = self.env["discuss.channel"].search(
                [
                    ("channel_type", "=", "chat"),
                    ("channel_member_ids.partner_id", "in", [user.partner_id.id]),
                ],
                limit=1,
            )
            if not channel:
                channel = self.env["discuss.channel"].create(
                    {
                        "name": user.name,
                        "channel_type": "chat",
                        "channel_member_ids": [
                            (0, 0, {"partner_id": user.partner_id.id})
                        ],
                    }
                )
            # Gửi tin nhắn
            self.env["mail.message"].create(
                {
                    "body": message_body,
                    "subject": "Notification: A new partner has been created",
                    "model": "discuss.channel",
                    "res_id": channel.id,
                    "message_type": "comment",
                    "partner_ids": [(4, user.partner_id.id)],
                }
            )

    def action_create_user(self):
        """Open a wizard to select a job title before creating a user from the partner"""
        self.ensure_one()
        # if self.user_ids:
        #     raise ValidationError("❌ This partner already has user account(s)!")
        if not self.env.user.has_group("realty_bds.access_group_full_users"):
            raise AccessError("You are not allowed to create a user from the partner!")
        if not self.password:
            raise ValidationError("The partner already has a use!")
        # Open wizard
        return {
            "type": "ir.actions.act_window",
            "name": "Choose Job Title",
            "res_model": "create.user.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "default_name": self.name,
                "default_email": self.email,
                "default_password": self.password,
                "default_citizen_id": self.citizen_id,
                "default_province_id": self.province_id.id,
                "default_district_id": self.district_id.id,
                "default_commune_id": self.commune_id.id,
                "default_province_resident_id": self.province_resident_id.id,
                "default_district_resident_id": self.district_resident_id.id,
                "default_commune_resident_id": self.commune_resident_id.id,
            },
        }

    def action_delete_partner(self):
        """Delete partner"""
        self.ensure_one()
        if not self.env.user.has_group("realty_bds.access_group_full_users"):
            raise AccessError("You are not allowed to delete this partner!")
        try:
            partner_name = self.name
            self.sudo().unlink()
            self.env["bus.bus"]._sendone(
                self.env.user.partner_id,
                "simple_notification",
                {
                    "title": "Thành công",
                    "message": f"Partner {partner_name} was successfully deleted!",
                    "type": "success",
                    "sticky": False,
                },
            )
            return {
                "type": "ir.actions.act_url",
                "url": "/web#action=base.action_partner_form&model=res.partner&view_type=list",
                "target": "self",
            }
        except Exception as e:
            raise ValidationError(f"Error: Delete partner: {str(e)}")

    # Helper method
    def is_subscribed_to(self, target_partner):
        """Return True if current partner subscribes to target_partner."""
        return target_partner.id in self.subscribed_partner_ids.ids
