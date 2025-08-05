from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore
from odoo.http import request # type: ignore

class ProductReport(models.Model):
    _name = 'product_report'
    _description = 'Real Estate Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

		# Attributes
    name = fields.Char(string='Name', required=True, tracking=True)
    customer = fields.Char(string='Customer', required=True, tracking=True)
    citizen_id = fields.Char(string='Citizen ID', required=True, tracking=True)
    phone = fields.Char(string='Phone', required=True, tracking=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    opinions = fields.Text(string='Initial Opinions', required=True, tracking=True)
    other_reason = fields.Text(string='Other Reason', help="Enter your reason if you selected 'Other'.", tracking=True)
    other_owner_feedback = fields.Text(string='Other Owner Feedback', help="Enter your owner feedback if you selected 'Other'.", tracking=True)    
    other_client_feedback = fields.Text(string='Other Client Feedback', help="Enter your client feedback if you selected 'Other'.", tracking=True)
    approval = fields.Selection(
        [
            ('pending',  'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval',
        default='pending',
        tracking=True,
    )
    
    # Relationship Attributes
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='restrict', tracking=True)
    product_id = fields.Many2one('product.template', string='Product', required=True, ondelete='cascade', tracking=True)
    img_ids = fields.Many2many(
				'ir.attachment', 
				required=True, 
				string='Images', 
				domain="[('mimetype', 'like', 'image/%')]"
		)
    
		# Compute Attributes
    reason = fields.Text(
        compute='_compute_reason',
        store=True,
        string="True Reason",
        help='Stores the final reason (predefined or custom text).',
        tracking=True
    )        
    owner_feedback = fields.Text(
        compute='_compute_owner_feedback',
        store=True,
        string="True Owner Feedback",
        help='Stores the final owner feedback (predefined or custom text).',
        tracking=True
    )        
    client_feedback = fields.Text(
        compute='_compute_client_feedback',
        store=True,
        string="True Client Feedback",
        help='Stores the final client feedback (predefined or custom text).',
        tracking=True
    )       

    @api.depends('reason_selection', 'other_reason')
    def _compute_reason(self):
        for report in self:
            if report.reason_selection == 'other':
                report.reason = report.other_reason  # Store custom text
            elif report.reason_selection:
                report.reason = report.reason_selection  # Store predefined reason
            else:
                report.reason = False

    @api.depends('owner_feedback_selection', 'other_owner_feedback')
    def _compute_owner_feedback(self):
        for report in self:
            if report.owner_feedback_selection == 'other':
                report.owner_feedback = report.other_owner_feedback  # Store custom text
            elif report.owner_feedback_selection:
                report.owner_feedback = report.owner_feedback_selection  # Store predefined reason
            else:
                report.owner_feedback = False
                
    @api.depends('client_feedback_selection', 'other_client_feedback')
    def _compute_client_feedback(self):
        for report in self:
            if report.client_feedback_selection == 'other':
                report.client_feedback = report.other_client_feedback  # Store custom text
            elif report.client_feedback_selection:
                report.client_feedback = report.client_feedback_selection  # Store predefined reason
            else:
                report.client_feedback = False
    
		# Selection Attributes
    reason_selection = fields.Selection(
        selection='_get_reason_selection',
        string='Reason to Buy',
        help="Choose a predefined reason or 'Other' to enter a custom reason."
    )
    client_feedback_selection = fields.Selection(
        selection='_get_client_feedback_selection',
        string='Client Feedback',
        help="Choose a predefined client feedback or 'Other' to enter a custom client feedback."
    )
    owner_feedback_selection = fields.Selection(
        selection='_get_owner_feedback_selection',
        string='Owner Feedback',
        help="Choose a predefined owner feedback or 'Other' to enter a custom owner feedback."
    )
    
    @api.model
    def _get_reason_selection(self):
        reasons = self.env['reasons_buy'].search([])
        return [(reason.name, reason.name) for reason in reasons] + [('other', 'Other')]
    
    @api.model
    def _get_owner_feedback_selection(self):
        owner_feedbacks = self.env['owner_feedback'].search([])
        return [(owner_feedback.name, owner_feedback.name) for owner_feedback in owner_feedbacks] + [('other', 'Other')]
    
    @api.model
    def _get_client_feedback_selection(self):
        client_feedbacks = self.env['client_feedback'].search([])
        return [(client_feedback.name, client_feedback.name) for client_feedback in client_feedbacks] + [('other', 'Other')]
    
    # Constrain
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'This name already exists!'),  # Ensure uniqueness
    ]

    @api.constrains('name')
    def _check_name(self):
        # Fetch reserved words dynamically from the policy model
        reserved_words = request.env['policy'].sudo().search([]).mapped('name')
        reserved_words = set(word.strip().lower() for word in reserved_words)  # Normalize        
        for record in self:
            clean_name = record.name.strip().lower()  # Convert to lowercase to check correctly
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError('❌ Error: Name cannot be empty or contain only spaces!')
            if len(record.name) > 100:  # Limit name length
                raise ValidationError('❌ Error: Name cannot exceed 100 characters!')
            if any(char in record.name for char in r"@#$%&*<>?/|{}[]\\!+=;:,"):  # Block special characters
                raise ValidationError('❌ Error: Name cannot contain special characters!')
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(f"❌ Error: Name '{record.name}' is not allowed!")