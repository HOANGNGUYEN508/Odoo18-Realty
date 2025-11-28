from odoo import models, fields, api  # type: ignore
from odoo.exceptions import UserError, AccessError, ValidationError  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class UserEvaluation(models.Model):
    _name = "user_evaluation"
    _description = "User Account Evaluation"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # For chatter and activities

    # Attributes
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="pending",
        required=True,
        tracking=True,
    )
    email = fields.Char(string="Email", required=True, tracking=True)
    citizen_id = fields.Char(string="Citizen ID", tracking=True)
    phone = fields.Char(string="Phone", tracking=True)
    note = fields.Text(string="Moderator Notes")
    reason = fields.Text(string="Rejection Reason")
    moderated_on = fields.Datetime(string="Moderated On")

    # Relationship Attributes
    province_id = fields.Many2one("res.country.state", string="Hometown Province")
    district_id = fields.Many2one("district", string="Hometown District")
    commune_id = fields.Many2one("commune", string="Hometown Commune")
    province_resident_id = fields.Many2one(
        "res.country.state", string="Permanent Address Province"
    )
    district_resident_id = fields.Many2one(
        "district", string="Permanent Address District"
    )
    commune_resident_id = fields.Many2one("commune", string="Permanent Address Commune")
    signup_company_id = fields.Many2one("res.company", string="Requested Company")
    document_id = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Documents",
        domain=[("res_model", "=", "user_evaluation")],
        help="Identity documents uploaded during signup",
    )
    user_id = fields.Many2one(
        "res.users", string="User", required=True, ondelete="cascade", tracking=True
    )
    moderator_id = fields.Many2one(
        "res.users", string="Assigned Moderator", tracking=True
    )

    # Action
    def action_schedule(self):
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.ensure_one()  # Ensure only one record is selected
        if self.state != "pending":
            raise UserError("❌ Error: No longer need to schedule a metting anymore.")

        # Calculate start (current time) and end (1 hour later)
        start = fields.Datetime.now()
        stop = fields.Datetime.add(start, hours=1)

        # Get the model ID for product.template
        model_id = self.env["ir.model"]._get_id("user_evaluation")

        # Prepare attendees: current user + product owner (if different)
        partner_ids = [self.env.user.partner_id.id]
        owner_partner = self.create_uid.partner_id
        if owner_partner.id != self.env.user.partner_id.id:
            partner_ids.append(owner_partner.id)

        # Open calendar event creation dialog
        return {
            "type": "ir.actions.act_window",
            "res_model": "calendar.event",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_name": f"Meeting: {self.user_id.name}",
                "default_start": start,
                "default_stop": stop,
                "default_res_model_id": model_id,
                "default_res_id": self.id,  # Current ID
                "default_user_id": self.env.user.id,  # Current user as organizer
                "default_partner_ids": [(6, 0, partner_ids)],  # Attendees
            },
        }

    def action_approve(self):
        """Approve evaluation and transfer documents to partner."""
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.check_action("approve")

        user = self.user_id
        if not user or not user.exists():
            raise UserError(
                f"action_approve: linked user not found for evaluation id {self.id}"
            )

        partner = user.partner_id
        if not partner or not partner.exists():
            raise UserError(
                f"action_approve: user {user.name} has no partner to update."
            )
        try:
            default_job_id = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(f"realty_bds.default_job_id_{user.company_id.id}", default=False)
            )

            if default_job_id:
                job = self.env["hr.job"].browse(default_job_id)
                if job.exists() and job.active:
                    user.sudo().write({"hr_job_id": job.id})
        except (ValueError, TypeError) as e:
            _logger.warning(f"Error: {e}")
            
        try:
            # Update partner fields
            vals = {
                "phone": self.phone or False,
                "citizen_id": self.citizen_id or False,
                "province_resident_id": (
                    self.province_resident_id.id if self.province_resident_id else False
                ),
                "district_resident_id": (
                    self.district_resident_id.id if self.district_resident_id else False
                ),
                "commune_resident_id": (
                    self.commune_resident_id.id if self.commune_resident_id else False
                ),
                "province_id": self.province_id.id if self.province_id else False,
                "district_id": self.district_id.id if self.district_id else False,
                "commune_id": self.commune_id.id if self.commune_id else False,
                "moderator_id": self.env.user.id,
                "moderated_on": fields.Datetime.now(),
            }
            partner.sudo().write(vals)

            # Transfer documents from user_evaluation to res.partner
            if self.document_id:
                attachment_vals = {
                    "res_model": "res.partner",
                    "res_id": partner.id,
                }
                self.document_id.sudo().write(attachment_vals)

        except Exception as e:
            _logger.exception(
                "action_approve: failed to update partner or transfer documents for evaluation %s: %s",
                self.id,
                e,
            )
            raise UserError(f"Failed to approve evaluation: {str(e)}")

    def action_note(self):
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.check_action("note")

        # Return action to open the reject wizard
        return {
            "name": "Taking Note",
            "type": "ir.actions.act_window",
            "res_model": "user_evaluation_wizard",
            "view_mode": "form",
            "views": [(self.env.ref("realty_bds.view_reject_user_wizard").id, "form")],
            "target": "new",
            "context": {
                "default_action_type": "note",
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }

    def action_reject(self):
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.check_action("reject")

        # Return action to open the reject wizard
        return {
            "name": "Reject User",
            "type": "ir.actions.act_window",
            "res_model": "user_evaluation_wizard",
            "view_mode": "form",
            "views": [(self.env.ref("realty_bds.view_reject_user_wizard").id, "form")],
            "target": "new",
            "context": {
                "default_action_type": "reject",
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }

    # Helper method
    def check_action(self, action):
        # will later override in child models to use action
        self.ensure_one()

        group_dict = (
            self.env["permission_tracker"]._get_permission_groups("res.users") or {}
        )

        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")

        # Check if user has the moderator group
        if not (
            self.env.user.has_group(moderator_group)
            or self.env.user.has_group(realty_group)
        ):
            raise AccessError(
                f"You don't have the necessary permissions to {action} posts."
            )

        # Check company permission (pass if user is in access_group_realty_urgent_buying)
        if not self.env.user.has_group(realty_group):
            if self.company_id != self.env.user.company_id and self.company_id.id != 1:
                raise AccessError(f"You can only {action} posts from your own company.")

    # Model Method
    @api.model
    def create_from_signup(self, user, user_data, moderator=None):
        """
        Create a user_evaluation record from signup.
        - user: res.users record (the newly created user)
        - user_data: dict with keys like citizen_id, phone, province_id, district_id, commune_id, province_resident_id, district_resident_id, commune_resident_id, signup_company_id
        - moderator: optional res.users record to assign as moderator
        Returns the created user_evaluation record (sudo).
        """
        if not user:
            raise ValueError("user is required to create user_evaluation")

        # map incoming fields carefully and normalize falsy ints (0) to False
        signup_company = user_data.get("signup_company_id") or False
        vals = {
            "user_id": int(user.id),
            "email": str(user.login or user.email or ""),
            "citizen_id": user_data.get("citizen_id") or False,
            "phone": user_data.get("phone") or False,
            "province_id": user_data.get("province_id") or False,
            "district_id": user_data.get("district_id") or False,
            "commune_id": user_data.get("commune_id") or False,
            "province_resident_id": user_data.get("province_resident_id") or False,
            "district_resident_id": user_data.get("district_resident_id") or False,
            "commune_resident_id": user_data.get("commune_resident_id") or False,
            "signup_company_id": int(signup_company) if signup_company else False,
            "state": "pending",
        }
        if moderator and moderator.exists():
            vals["moderator_id"] = int(moderator.id)

        # create with sudo to bypass access issues during signup flow
        rec = self.sudo().create(vals)
        return rec

    @api.ondelete(at_uninstall=False)
    def _unlink_users(self):
        """Delete related hr.employee, res.users, and res.partner records when evaluation is deleted.

        Delegates to hr.employee's terminate_employee method for proper cleanup.
        Only processes rejected evaluations.
        Handles both active and archived users.
        """
        if not self:
            return

        # Only process rejected evaluations
        rejected_evals = self.filtered(lambda e: e.state == "rejected")
        if not rejected_evals:
            return

        HrEmployee = self.env["hr.employee"].sudo()
        ResUsers = self.env["res.users"].sudo()

        # Collect all user IDs from rejected evaluations
        user_ids = rejected_evals.mapped("user_id").filtered(lambda u: u.exists())
        if not user_ids:
            return

        # Find all employees associated with these users (including archived)
        employees = HrEmployee.with_context(active_test=False).search(
            [("user_id", "in", user_ids.ids)]
        )

        if employees:
            try:
                # Delegate to hr.employee's termination method
                employees.terminate_employee()
            except Exception as e:
                _logger.exception(
                    "Failed to terminate employees during evaluation deletion: %s", e
                )
        else:
            # No employees found, but still need to clean up users and partners
            ResPartner = self.env["res.partner"].sudo()
            partners = user_ids.mapped("partner_id").filtered(lambda p: p.exists())

            # Delete users
            try:
                user_ids.unlink()
            except Exception as e:
                _logger.exception("Failed to delete users: %s", e)
                return

            # Check and delete orphaned partners
            if partners:
                partners_to_delete = ResPartner.browse()
                for partner in partners:
                    if partner.exists():
                        remaining_users = ResUsers.with_context(
                            active_test=False
                        ).search([("partner_id", "=", partner.id)], limit=1)
                        if not remaining_users:
                            partners_to_delete |= partner

                if partners_to_delete:
                    try:
                        partners_to_delete.unlink()
                    except Exception as e:
                        _logger.exception("Failed to delete orphaned partners: %s", e)

    # Restraint
    @api.constrains("note")
    def _check_note(self):
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )
        for record in self:
            clean_note = record.note.strip().lower() if record.note else ""
            if not record.note.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Note cannot be empty or contain only spaces!"
                )
            if len(record.note) > 300:
                raise ValidationError("❌ Error: Note cannot exceed 300 characters!")
            if any(
                char in record.note for char in r"@#$%&*<>?/|{}[]\\!+=;:,"
            ):  # Block special characters
                raise ValidationError(
                    f"❌ Error: Note cannot contain special characters ({r'@#$%&*<>?/|{}[]\!+=;:,'})!"
                )
            match = next((w for w in reserved_words if w in clean_note), None)
            if match:
                raise ValidationError(
                    f"❌ Error: Note contains reserved word: '{match}'!"
                )
