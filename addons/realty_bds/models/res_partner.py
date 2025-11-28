from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Attributes
    citizen_id = fields.Char(string="Số CCCD", tracking=True)
    moderated_on = fields.Datetime(string="Moderated On")

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
    subscriber_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="partner_subscribe_rel",
        column1="partner_id",
        column2="subscribed_partner_id",
        string="Subscribers",
    )
    moderator_id = fields.Many2one("res.users", string="Moderator")
    document_id = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Documents",
        domain=[("res_model", "=", "res.partner")],
        help="Identity documents after evaluation",
    )

    # Compute Attributes
    is_user = fields.Boolean(
        string="Is a System User", compute="_compute_has_user", store=False
    )

    @api.depends("user_ids")
    def _compute_has_user(self):
        for r in self:
            r.is_user = bool(r.user_ids)

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

    @api.onchange("province_resident_id")
    def _onchange_province_resident_id(self):
        """Reset resident district and commune when resident province changes"""
        for record in self:
            if record.province_resident_id:
                # Check if current resident district belongs to new resident province
                if (
                    record.district_resident_id
                    and record.district_resident_id.province_id
                    != record.province_resident_id
                ):
                    record.district_resident_id = False
                # Always reset resident commune when resident province changes
                record.commune_resident_id = False
            else:
                # If resident province is cleared, clear resident district and commune
                record.district_resident_id = False
                record.commune_resident_id = False

    @api.onchange("district_resident_id")
    def _onchange_district_resident_id(self):
        """Reset resident commune when resident district changes"""
        for record in self:
            if record.district_resident_id:
                # Check if current resident commune belongs to new resident district
                if (
                    record.commune_resident_id
                    and record.commune_resident_id.district_id
                    != record.district_resident_id
                ):
                    record.commune_resident_id = False
            else:
                # If resident district is cleared, clear resident commune
                record.commune_resident_id = False

    # Action
    def action_toggle_subscribe(self):
        self.ensure_one()
        current_partner = self.env.user.partner_id
        if not current_partner:
            return {"subscribed": False}

        if current_partner.id in self.subscriber_partner_ids.ids:
            # remove current_partner from this partner's subscribers
            self.sudo().write({"subscriber_partner_ids": [(3, current_partner.id)]})
            return {"subscribed": False}
        else:
            self.sudo().write({"subscriber_partner_ids": [(4, current_partner.id)]})
            return {"subscribed": True}

    # Helper method
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
        if self.is_user:
            raise ValidationError("❌ This partner already has user account(s)!")
        if self.is_company:
            raise ValidationError("❌ Cannot create user for a company partner!")
        
        group_dict = (
            self.env["permission_tracker"]._get_permission_groups("res.users") or {}
        )
        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")
        if not (
            self.env.user.has_group(moderator_group)
            or self.env.user.has_group(realty_group)
        ):
            raise AccessError(
                "You don't have the necessary permissions to perform this action."
            )

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
            },
        }

    # Method
    @api.ondelete(at_uninstall=False)
    def _unlink_partner_documents(self):
        IrAttachment = self.env["ir.attachment"]

        for post in self:
            all_attachments = post.document_id
            if all_attachments:
                attachment_ids = all_attachments.ids
                IrAttachment.mark_orphaned(attachment_ids, self._name, post.id)
