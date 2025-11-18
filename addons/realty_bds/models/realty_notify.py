from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, UserError, AccessError  # type: ignore
from odoo.http import request  # type: ignore
from markupsafe import Markup  # type: ignore
import html
import logging

_logger = logging.getLogger(__name__)


class Notify(models.AbstractModel):
    _name = "notify"
    _description = "Realty Abstract Notify - Guideline, Notification, Urgent Buying or Congratulation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    # Attributes
    name = fields.Char(string="Tittle", required=True, help="", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)
    approval = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("removed", "Removed"),
        ],
        string="Approval",
        default="draft",
        tracking=True,
    )
    reason = fields.Text(
        string="Reason for Rejection/Removal",
        help="Why the post was rejected/removed",
        tracking=True,
    )
    content = fields.Text(string="Content", tracking=True)
    moderated_on = fields.Datetime(string="Moderated On")
    edit_counter = fields.Integer(
        string="Edit Counter",
        default=-1,
        help="Number of times the post can be edited after rejected",
        required=True,
        tracking=True,
    )

    # Relationship Attributes
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    moderator_id = fields.Many2one("res.users",
                                   string="Moderator",
                                   help="User who approved/rejected this post")
    # Computed Attribute
    comment_count = fields.Integer(
        string="Comment Count",
        default=0)
    
    # Action
    def action_open_comments(self):
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.ensure_one()
        group_dict = self.env["permission_tracker"]._get_permission_groups(
            self._name) or {}
        return {
            "type": "ir.actions.client",
            "tag": "realty_comment_dialog_action",
            "params": {
                "res_model": self._name,
                "res_id": self.id,
                "group": group_dict,
            },
        }

    def action_send(self):
        self.ensure_one()
        if self.create_uid != self.env.user:
            raise UserError(
                "❌ Error: You can only send your own post for approval.")
        if self.approval == "pending":
            raise UserError("❌ Error: Wait for approval.")
        if self.approval != "draft":
            raise UserError(
                "❌ Error: Only posts in 'Draft' state can be send for approval."
            )
        if self.edit_counter != -1:
            raise UserError(
                "❌ Error: This is not the first time you send this.")
        self.approval = "pending"
        self._assign_moderator_after_send()

    def action_resend(self):
        self.ensure_one()
        if self.create_uid != self.env.user:
            raise UserError(
                "❌ Error: You can only send your own post for approval.")
        if self.approval == "pending":
            raise UserError("❌ Error: Wait for approval.")
        if self.approval != "rejected":
            raise UserError(
                "❌ Error: Only posts in 'Rejected' state can be resend for approval."
            )
        if self.edit_counter == 0:
            raise UserError("❌ Error: You have exhausted your edit attempts.")
        self.approval = "pending"
        self._assign_moderator_after_send()

    def action_approve(self):
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.check_action("approve")

        self.approval = "approved"
        self.moderator_id = self.env.user
        self.moderated_on = fields.Datetime.now()
        self._notify_subscribers()

    def action_reject(self):
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.check_action("reject")

        # Return action to open the reject wizard
        return {
            "name":
            "Reject Post",
            "type":
            "ir.actions.act_window",
            "res_model":
            "notify_wizard",
            "view_mode":
            "form",
            "views":
            [(self.env.ref("realty_bds.view_generic_wizard_form").id, "form")],
            "target":
            "new",
            "context": {
                "default_action_type": "reject",
                "default_res_model": self._name,  # Pass the model name
                "default_res_id": self.id,  # Pass the record ID
            },
        }

    def action_remove(self):
        if not self or not self.exists():
            raise UserError(
                "The record no longer exists (deleted by another user). Please refresh the view."
            )
        self.check_action("remove")

        # Return action to open the remove wizard
        return {
            "name":
            "Remove Post",
            "type":
            "ir.actions.act_window",
            "res_model":
            "notify_wizard",
            "view_mode":
            "form",
            "views":
            [(self.env.ref("realty_bds.view_generic_wizard_form").id, "form")],
            "target":
            "new",
            "context": {
                "default_action_type": "remove",
                "default_res_model": self._name,  # Pass the model name
                "default_res_id": self.id,  # Pass the record ID
            },
        }

    # Helper method
    def check_action(self, action):
        # will later override in child models to use action
        self.ensure_one()

        group_dict = self.env["permission_tracker"]._get_permission_groups(
            self._name) or {}

        moderator_group = group_dict.get("moderator_group")
        realty_group = group_dict.get("realty_group")

        # Check if user has the moderator group
        if not (self.env.user.has_group(moderator_group)
                or self.env.user.has_group(realty_group)):
            raise AccessError(
                f"You don't have the necessary permissions to {action} posts.")

        # Check company permission (pass if user is in access_group_realty_urgent_buying)
        if not self.env.user.has_group(realty_group):
            if self.company_id != self.env.user.company_id and self.company_id.id != 1:
                raise AccessError(
                    f"You can only {action} posts from your own company.")

    def _notify_subscribers(self):
        self.ensure_one()
        author_partner = self.create_uid.partner_id
        # find partners who subscribed to the author
        subscribers = (author_partner.subscriber_partner_ids - author_partner)
        if not subscribers:
            return
        body_html = f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; color: white;">
                    <h2 style="margin: 0; font-size: 24px;">📢 New Post Notification</h2>
                </div>
                
                <div style="padding: 25px; background: #f9f9f9;">
                    <div style="background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <p style="font-size: 16px; margin-bottom: 15px;">
                            <strong>{html.escape(author_partner.name)}</strong> has shared a new post in <strong>{self._name}</strong>.
                        </p>
                        
                        <div style="border-left: 4px solid #667eea; padding-left: 15px; margin: 20px 0; background: #f8f9fa; padding: 15px;">
                            <h3 style="margin-top: 0; color: #2c3e50; font-size: 18px;">
                                {html.escape(self.name)}
                            </h3>
                        </div>
                        
                        <div style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #eee;">
                            <p style="font-size: 14px; color: #666;">
                                💡 <em>This notification was sent because you are subscribed to {html.escape(author_partner.name)}'s updates.</em>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
            """
        # Post a mail.message first (use sudo to avoid rights issues)
        msg = self.sudo().message_post(
            body=Markup(body_html),
            subject="New post",
            subtype_xmlid='mail.mt_comment',
        )

        # Create mail.notification entries explicitly
        notif_model = self.env['mail.notification'].sudo()
        notif_vals = []
        for partner in subscribers:
            if partner.id == author_partner.id:
                continue
            notif_vals.append({
                'res_partner_id': partner.id,
                'notification_type':
                'inbox',  # makes it appear in Discuss -> Inbox
                'mail_message_id': msg.id,
                'is_read': False,
            })
        if notif_vals:
            notif_model.create(notif_vals)

    def _assign_moderator(self):
        """Assign a moderator using round-robin distribution"""
        company_id = self.env.company.id

        group_dict = self.env["permission_tracker"]._get_permission_groups(
            self._name) or {}

        moderator_group = group_dict.get("moderator_group")

        # Get the moderator group
        group = self.env.ref(moderator_group, raise_if_not_found=False)
        if not group:
            _logger.error(f"Moderator group {moderator_group} not found")
            return None

        # Get moderators for the company and group
        moderators = (self.env["res.users"].sudo().search(
            [("groups_id", "in", group.id), ("company_id", "=", company_id)],
            order="id",
        ))

        if not moderators:
            _logger.warning(
                f"No moderators found for group {group.name} in company {company_id}"
            )
            return None

        # Use advisory lock to prevent race conditions
        lock_key = f"moderator_assignment_{company_id}_{group.id}_{self._name}"
        try:
            self.env.cr.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                                (lock_key, ))
        except Exception:
            _logger.exception("Failed to acquire advisory lock for %s",
                              lock_key)
            raise UserError("Could not acquire database lock, try again.")

        # Get or create sequence record for this company, group, and model
        sequence_model = self.env["moderator_assignment_sequence"]
        sequence = sequence_model.get_or_create_sequence(
            company_id, group.id, self._name)

        # Get next moderator
        next_moderator = sequence.get_next_moderator(moderators)
        if next_moderator:
            sequence.update_sequence(next_moderator)
            return next_moderator.id

        return None

    def _assign_moderator_after_send(self):
        """Assign moderator after send/resend - common logic for all child models"""
        moderator_id = self._assign_moderator()
        if moderator_id:
            self.moderator_id = moderator_id
        else:
            _logger.warning(
                f"No moderator assigned for {self._name} post ID {self.id}")

    # Model method
    def compute_comment_count(self, type):
        """
        Update comment count with sudo rights
        :param type: Boolean - True to increment, False to decrement
        """
        if not self:
            return
        
        # Validate input type
        if type not in [True, False]:
            raise UserError("Type parameter must be boolean (True/False)")
        
        # Calculate new count values for each record
        update_vals = {}
        for record in self:
            current_count = record.comment_count or 0
            
            if type:  # True = increment
                new_count = current_count + 1
            else:  # False = decrement
                new_count = max(0, current_count - 1)  # Ensure never goes below 0
            
            update_vals[record.id] = new_count
        
        # Apply updates with sudo rights
        for record in self:
            record.sudo().write({'comment_count': update_vals[record.id]})

    @api.model_create_multi
    def create(self, vals_list):
        # Enforce single record creation
        if len(vals_list) > 1:
            raise UserError("Only one record can be created at a time.")

        vals = vals_list[0]

        vals["company_id"] = self.env.company.id

        # Create the single record
        records = super().create([vals])
        for record in records:
            try:
                all_attachments = record.img_ids

                if all_attachments:
                    attachment_ids = all_attachments.ids
                    self.env['ir.attachment'].mark_true(attachment_ids)
            except Exception as e:
                _logger.error(
                    "Failed to mark attachments as saved for record %s: %s",
                    record.id, str(e))
        return records

    def unlink(self):
        # collect attachments before deleting (so we know which records were involved)
        self.ensure_one()
        res_id = self.id
        res_model = self._name

        # delete the records (this removes the M2M relation rows)
        res = super().unlink()

        # clear all comment of this post
        comments_to_clear = self.env["realty_comment"].sudo().search([
            ("res_model", "=", res_model), ("res_id", "=", res_id),
            ("parent_id", "=", False)
        ])

        if comments_to_clear:
            comments_to_clear.with_context(
                skip_realty_delete_custom=True).unlink()
        # Push bus to whoever still open the comment section of this pos
        try:
            bus = self.env["bus.bus"]
            bus._sendone(
                f"realty_comment_{res_model}_{res_id}",
                "realty_notify",
                {"type": "absolute_delete"},
            )
        except Exception:
            _logger.info("bus.bus not available; skipping realty_comment push")
            pass
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_post_attachments(self):
        IrAttachment = self.env['ir.attachment']

        for post in self:
            all_attachments = post.img_ids
            if all_attachments:
                attachment_ids = all_attachments.ids
                IrAttachment.mark_orphaned(attachment_ids, self._name, post.id)

    # Constrains
    @api.constrains("name", "content")
    def _check_name_content(self):
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )

        for record in self:
            clean_name = record.name.strip().lower() if record.name else ""
            clean_content = record.content.strip().lower(
            ) if record.content else ""
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Tittle cannot be empty or contain only spaces!")
            if len(record.name) > 100:  # Limit name length
                raise ValidationError(
                    "❌ Error: Tittle cannot exceed 100 characters!")
            match_name = next((w for w in reserved_words if w in clean_name),
                              None)
            if match_name:
                raise ValidationError(
                    f"❌ Error: Name contains reserved word: '{match_name}'!")
            if len(record.content) > 1000:  # Limit name length
                raise ValidationError(
                    "❌ Error: Content cannot exceed 1000 characters!")
            match_content = next(
                (w for w in reserved_words if w in clean_content), None)
            if match_content:
                raise ValidationError(
                    f"❌ Error: Content contains reserved word: '{match_content}'!"
                )

    @api.constrains("reason", "approval")
    def _check_reason(self):
        for record in self:
            if record.approval == "rejected" and not record.reason:
                raise ValidationError(
                    "❌ Error: Reason for rejection must be provided when the post is rejected."
                )
            if record.approval != "rejected" and record.reason:
                raise ValidationError(
                    "❌ Error: Reason should only be provided when the post is rejected."
                )
