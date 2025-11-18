from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class ResUsers(models.Model):
    _inherit = "res.users"

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
    province_resident_id = fields.Many2one(
        "res.country.state", string="Residence Province/City ", ondelete="restrict"
    )
    district_resident_id = fields.Many2one(
        "district",
        string="Residence District/Town",
        domain="[('province_id', '=', province_resident_id)]",
        ondelete="restrict",
    )
    commune_resident_id = fields.Many2one(
        "commune",
        string="Residence Commune",
        domain="[('district_id', '=', district_resident_id)]",
        ondelete="restrict",
    )
    hr_job_id = fields.Many2one(
        "hr.job",
        string="Chức danh",
        help="The job title associated with this user",
        ondelete="restrict",
    )

    # Helper Method
    BLOCKED_GROUP_XML_IDS = [
        "product.group_product_manager",
        "base.group_sanitize_override",
        "website.group_website_designer",
        "hr.group_hr_manager",
        "website.group_website_restricted_editor",
        "hr.group_hr_user",
    ]

    def _sync_groups_from_job_title(self):
        # Get all blocked groups
        blocked_groups = self.env["res.groups"]
        for xmlid in self.BLOCKED_GROUP_XML_IDS:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                blocked_groups |= group

        for user in self:
            if user.hr_job_id:
                # Get job's groups minus blocked ones
                job_groups = user.hr_job_id.implied_ids - blocked_groups

                # Get current non-blocked groups
                current_groups = user.groups_id - blocked_groups

                # Merge and set groups
                user.groups_id = current_groups | job_groups
            else:
                # Just remove blocked groups (keep others)
                user.groups_id = [(3, group.id) for group in blocked_groups]

    def _sync_to_partner(self):
        for user in self:
            if not user.partner_id:
                continue
            partner_vals = {
                "name": user.name,
                "email": user.login,
                "company_id": user.company_id.id,
                "citizen_id": user.citizen_id,
                "province_id": user.province_id,
                "district_id": user.district_id,
                "commune_id": user.commune_id,
                "province_resident_id": user.province_resident_id,
                "district_resident_id": user.district_resident_id,
                "commune_resident_id": user.commune_resident_id,
            }
            try:
                user.partner_id.write(partner_vals)
            except Exception as e:
                raise ValidationError(f"❌ Error syncing user to partner: {str(e)}")

    def notify_admin_empty_position(self):
        users_without_job_title = self.env["res.users"].search(
            [("hr_job_id", "=", False)]
        )
        if not users_without_job_title:
            return
        group_xml_ids = ["realty_bds.access_group_full_users"]
        group_ids = [self.env.ref(xml_id).id for xml_id in group_xml_ids]
        users_to_notify = self.env["res.users"].search([("groups_id", "in", group_ids)])
        if not users_to_notify:
            return
        user_links = [
            f'<a href="/web#id={user.id}&model=res.users&view_type=form">{user.name}</a>'
            for user in users_without_job_title
        ]
        user_list_html = ", ".join(user_links) if user_links else "No users found"
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
            self.env["mail.message"].create(
                {
                    "body": f"{len(users_without_job_title)} new users have not been assigned a job title: {user_list_html}.",
                    "subject": "Notification: Users without job titles",
                    "model": "discuss.channel",
                    "res_id": channel.id,
                    "message_type": "comment",
                    "partner_ids": [(4, user.partner_id.id)],
                }
            )

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("password", "12345")

        # ─── 2) CREATE USERS ────────────────────────────────────────────────────────
        users = super().create(vals_list)

        # ─── 3) STRIP OUT UNWANTED GROUPS ───────────────────────────────────────────
        xml_ids_to_remove = [
            "product.group_product_manager",
            "base.group_sanitize_override",
            "website.group_website_designer",
            "hr.group_hr_manager",
            "website.group_website_restricted_editor",
            "hr.group_hr_user",
        ]
        group_ids_to_remove = []
        for xmlid in xml_ids_to_remove:
            grp = self.env.ref(xmlid, raise_if_not_found=False)
            if grp:
                group_ids_to_remove.append(grp.id)

        if group_ids_to_remove:
            # remove them from every new user
            users.write({"groups_id": [(3, g) for g in group_ids_to_remove]})

        self.notify_admin_empty_position()
        target_user = self.env['res.users'].browse(2)
        target_partner = target_user.partner_id if target_user.exists() else False
        for user, vals in zip(users, vals_list):
            # partner‑creation —
            if not user.partner_id:
                partner_vals = {
                    "name": user.name,
                    "email": user.login,
                    "company_id": user.company_id.id,
                    "citizen_id": user.citizen_id,
                    "province_id": user.province_id.id,
                    "district_id": user.district_id.id,
                    "commune_id": user.commune_id.id,
                    "province_resident_id": user.province_resident_id.id,
                    "district_resident_id": user.district_resident_id.id,
                    "commune_resident_id": user.commune_resident_id.id,
                }
                partner = self.env["res.partner"].create(partner_vals)
                user.partner_id = partner
                
            # ─ auto-subscribe to user id=2's partner ─
            if target_partner and user.partner_id:
                target_partner.sudo().write({'subscriber_partner_ids': [(4, user.partner_id.id)]})

            # — sync groups from job title —
            if vals.get("hr_job_id"):
                user._sync_groups_from_job_title()

            # — sync partner fields —
            user._sync_to_partner()

            # — employee record creation —
            if not self.env["hr.employee"].search([("user_id", "=", user.id)], limit=1):
                self.env["hr.employee"].create(
                    {
                        "name": user.name or user.login,
                        "work_email": user.email or user.login,
                        "user_id": user.id,
                        "job_id": user.hr_job_id.id if user.hr_job_id else False,
                    }
                )

        return users

    def write(self, vals):
        res = super(ResUsers, self).write(vals)
        for user in self:
            if not user.partner_id:
                partner_vals = {
                    "name": user.name,
                    "email": user.login,
                    "company_id": user.company_id.id,
                    "citizen_id": user.citizen_id,
                    "province_id": user.province_id,
                    "district_id": user.district_id,
                    "commune_id": user.commune_id,
                    "province_resident_id": user.province_resident_id,
                    "district_resident_id": user.district_resident_id,
                    "commune_resident_id": user.commune_resident_id,
                }
                partner = self.env["res.partner"].create(partner_vals)
                user.partner_id = partner
        if "hr_job_id" in vals:
            self._sync_groups_from_job_title()
        if any(
            field in vals
            for field in [
                "name",
                "email",
                "company_id",
                "citizen_id",
                "province_id",
                "district_id",
                "commune_id",
                "province_resident_id",
                "district_resident_id",
                "commune_resident_id",
            ]
        ):
            self._sync_to_partner()
        # Sync hr.employee
        for user in self:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", user.id)], limit=1
            )
            if employee:
                employee_vals = {}
                if "name" in vals:
                    employee_vals["name"] = vals["name"]
                if "email" in vals or "login" in vals:
                    employee_vals["work_email"] = vals.get("email") or vals.get("login")
                if "hr_job_id" in vals:
                    employee_vals["job_id"] = vals["hr_job_id"]
                if employee_vals:
                    employee.write(employee_vals)
        # Archive or unarchive for employee & partner
        if "active" in vals:
            for user in self:
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", user.id)], limit=1
                )
                if employee and employee.active != vals["active"]:
                    employee.active = vals["active"]
                if user.partner_id and user.partner_id.active != vals["active"]:
                    user.partner_id.active = vals["active"]
        return res

    # Constrains
    @api.constrains("hr_job_id")
    def _check_job_title_consistency(self):
        for user in self:
            if user.hr_job_id and not user.hr_job_id.active:
                raise ValidationError(
                    f"❌ Error: Job title: '{user.hr_job_id.name}' was disabled!"
                )

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
            if record.is_company or not record.user_ids:
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
            if record.is_company or not record.user_ids:
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
