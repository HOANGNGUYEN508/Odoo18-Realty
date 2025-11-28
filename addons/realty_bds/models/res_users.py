from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, UserError  # type: ignore
from markupsafe import Markup  # type: ignore
import html
import logging

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = "res.users"

    # Relationship Attributes
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

    def notify_signup_moderator(self, user_data):
        """Called after signup to create user_evaluation and notify the assigned moderator."""
        self.ensure_one()

        # Get moderator (res.users id) via your round-robin method
        moderator_id = self._assign_moderator()
        if not moderator_id:
            _logger.error("No moderator assigned for notifying new signup.")
            return

        moderator = self.env["res.users"].sudo().browse(int(moderator_id))
        target_partner_id = getattr(moderator.partner_id, "id", False)
        if not target_partner_id:
            _logger.error("Moderator %s has no partner to notify.", moderator.id)
            return

        # Create the user_evaluation record via model helper (defined below)
        try:
            # pass the user record (self), the user_data dict, and the moderator user record
            user_eval = (
                self.env["user_evaluation"]
                .sudo()
                .create_from_signup(user=self, user_data=user_data, moderator=moderator)
            )
        except Exception as e:
            _logger.exception("Failed to create user_evaluation record: %s", e)
            return

        # Build a compact HTML body (escape dynamic values)
        html_body = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
              <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; color: white;">
                <h2 style="margin: 0; font-size: 20px;">🎉 New user signup</h2>
              </div>
              <div style="padding: 20px; background: #f9f9f9;">
                <div style="background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.06);">
                  <p style="font-size: 14px; margin-bottom: 8px;">
                    <strong>{html.escape(self.name or '')}</strong> has just created an account.
                  </p>
                  <p style="font-size: 13px; color: #555; margin: 0;">
                    <strong>Email:</strong> {html.escape(str(self.login or self.email or ''))}
                  </p>
                </div>
              </div>
            </div>
            """

        # Post message to the created user_evaluation record (preferred)
        try:
            msg = user_eval.sudo().message_post(
                body=Markup(html_body),
                subject="New user signup",
                subtype_xmlid="mail.mt_note",
            )
        except Exception as e:
            _logger.warning("message_post on user_evaluation failed: %s", e)
            msg = None

        # Fallback: create mail.message if message_post failed
        if not msg:
            try:
                msg_vals = {
                    "model": user_eval._name,
                    "res_id": user_eval.id,
                    "body": Markup(html_body),
                    "subject": "New user signup",
                    "message_type": "notification",
                    "partner_ids": [(4, target_partner_id)],
                }
                msg = self.env["mail.message"].sudo().create(msg_vals)
            except Exception as e:
                _logger.error("Failed to create mail.message fallback: %s", e)
                return

        # Finally, add a mail.notification for the moderator partner (inbox)
        try:
            if msg and msg.exists():
                self.env["mail.notification"].sudo().create(
                    {
                        "res_partner_id": target_partner_id,
                        "notification_type": "inbox",
                        "mail_message_id": msg.id,
                        "is_read": False,
                    }
                )
        except Exception as e:
            _logger.warning("Failed to create mail.notification for moderator: %s", e)

        return user_eval

    def _assign_moderator(self):
        """Assign a moderator using round-robin distribution"""
        company_id = self.company_id.id
        group_dict = (
            self.env["permission_tracker"]._get_permission_groups(self._name) or {}
        )

        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")

        if company_id == 1:
            group = self.env.ref(realty_group, raise_if_not_found=False)
        else:
            group = self.env.ref(moderator_group, raise_if_not_found=False)
        if not group:
            _logger.error(
                "Moderator group for res.users not found in permission_tracker."
            )
            return None

        # Get moderators for the company and group
        moderators = self.sudo().search(
            [("groups_id", "in", group.id), ("company_id", "=", company_id)],
            order="id",
        )

        if not moderators:
            _logger.warning(
                f"No moderators found for group {group.name} in company {company_id}"
            )
            return None

        # Use advisory lock to prevent race conditions
        lock_key = f"moderator_assignment_{company_id}_{group.id}_{self._name}"
        try:
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))", (lock_key,)
            )
        except Exception:
            _logger.exception("Failed to acquire advisory lock for %s", lock_key)
            raise UserError("Could not acquire database lock, try again.")

        # Get or create sequence record for this company, group, and model
        sequence_model = self.env["moderator_assignment_sequence"]
        sequence = sequence_model.get_or_create_sequence(
            company_id, group.id, self._name
        )

        # Get next moderator
        next_moderator = sequence.get_next_moderator(moderators)
        if next_moderator:
            sequence.update_sequence(next_moderator)
            return next_moderator.id

        return None

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("password", "12345")

        # Create users
        users = super().create(vals_list)

        # Remove unwanted groups
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
            users.write({"groups_id": [(3, g) for g in group_ids_to_remove]})

        # Auto-subscribe to target user
        target_user = self.env["res.users"].browse(2)
        target_partner = target_user.partner_id if target_user.exists() else False

        for user, vals in zip(users, vals_list):
            # Sync groups from job title
            if vals.get("hr_job_id"):
                user._sync_groups_from_job_title()

            # Create employee record
            if not self.env["hr.employee"].search([("user_id", "=", user.id)], limit=1):
                self.env["hr.employee"].create(
                    {
                        "name": user.name or user.login,
                        "work_email": user.email or user.login,
                        "user_id": user.id,
                        "job_id": user.hr_job_id.id if user.hr_job_id else False,
                    }
                )

            # Auto-subscribe to target partner
            if target_partner and user.partner_id:
                target_partner.sudo().write(
                    {"subscriber_partner_ids": [(4, user.partner_id.id)]}
                )

        return users

    def write(self, vals):
        res = super(ResUsers, self).write(vals)

        if "hr_job_id" in vals:
            self._sync_groups_from_job_title()

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
