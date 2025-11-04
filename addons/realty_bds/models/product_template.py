from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, UserError, AccessError  # type: ignore
from odoo.http import request  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Attributes
    house_number = fields.Char(required=True,
                               string="House Number",
                               tracking=True)
    street = fields.Char(required=True, string="Street", tracking=True)
    real_estate_area = fields.Float(digits=(6, 3),
                                    required=True,
                                    string="Real Estate Area (m²)",
                                    tracking=True)
    usable_area = fields.Float(digits=(6, 3),
                               required=True,
                               string="Usable Area (m²)",
                               tracking=True)
    number_of_floors = fields.Integer(required=True,
                                      string="Number of Floors",
                                      tracking=True)
    frontage = fields.Float(digits=(6, 3),
                            required=True,
                            string="Frontage (m)",
                            tracking=True)
    presentation_image_id = fields.Integer(string="Presentation Image",
                                           tracking=True)
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
    moderated_on = fields.Datetime(string="Moderated On")
    edit_counter = fields.Integer(
        string="Edit Counter",
        default=-1,
        help="Number of times the post can be edited after rejected",
        required=True,
        tracking=True,
    )

    # Relationship Attributes
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id.id,
        tracking=True,
    )
    region_id = fields.Many2one("region",
                                required=True,
                                string="Region",
                                tracking=True)
    province_id = fields.Many2one("res.country.state",
                                  required=True,
                                  string="Province",
                                  tracking=True)
    commune_id = fields.Many2one("commune",
                                 required=True,
                                 string="Commune",
                                 tracking=True)
    district_id = fields.Many2one("district",
                                  required=True,
                                  string="District",
                                  tracking=True)
    type_id = fields.Many2one("type",
                              required=True,
                              string="Type",
                              tracking=True)
    status_id = fields.Many2one("status",
                                required=True,
                                string="Status",
                                tracking=True)
    land_title_id = fields.Many2one("land_title",
                                    required=True,
                                    string="Land Title",
                                    tracking=True)
    feature_ids = fields.Many2many("feature", required=True, string="Feature")
    home_direction_id = fields.Many2one("home_direction",
                                        string="Direction",
                                        tracking=True)  # Not required
    unit_price_id = fields.Many2one("unit_price",
                                    required=True,
                                    string="Unit Price",
                                    tracking=True)
    img_ids = fields.Many2many(
        "ir.attachment",
        relation="product_template_img_rel",
        required=True,
        string="Images",
        domain="[('mimetype', 'like', 'image/%')]",
    )
    private_img_ids = fields.Many2many(
        "ir.attachment",
        relation="product_template_private_img_rel", 
        required=True,
        string="Private Images",
        domain="[('mimetype', 'like', 'image/%')]",
    )
    shared_user_ids = fields.Many2many(
        "res.users",
        string="Shared with Users",
        help=
        "Users (in other companies, or same) who can also read this department.",
    )
    shared_company_ids = fields.Many2many(
        "res.company",
        string="Shared with Companies",
        help="All users in these companies can also read this department.",
    )
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

    # Compute Attributes
    attributes = fields.Char(compute="_compute_attributes",
                             store=False,
                             string="Attributes")
    price_per_sqm = fields.Char(compute="_compute_price_per_sqm",
                                store=False,
                                string="Million/m²")
    display_price = fields.Char(compute="_compute_display_price",
                                store=False,
                                string="Price")
    absolute_price = fields.Float(compute="_compute_absolute_price",
                                  store=True,
                                  string="Product True Price")
    address = fields.Char(compute="_compute_address",
                          store=False,
                          string="Address")

    @api.depends("house_number", "street", "commune_id", "district_id")
    def _compute_address(self):
        for rec in self:
            rec.address = f"{rec.house_number or ''} {rec.street or ''} {rec.commune_id.name or ''} {rec.district_id.name or ''}"

    @api.depends("list_price", "unit_price_id.multiplier")
    def _compute_absolute_price(self):
        for rec in self:
            rec.absolute_price = (rec.list_price
                                  or 0.0) * (rec.unit_price_id.multiplier or 1)

    @api.depends(
        "real_estate_area",
        "usable_area",
        "number_of_floors",
        "frontage",
        "home_direction_id",
    )
    def _compute_attributes(self):
        for rec in self:
            parts = []
            # Handle float fields with formatting
            for field in ["real_estate_area", "usable_area", "frontage"]:
                value = getattr(rec, field)
                if value:
                    formatted = round(value, 3) if value % 1 else int(value)
                    parts.append(str(formatted))
            # Handle other fields (int, m2o)
            for field in ["number_of_floors", "home_direction_id"]:
                value = getattr(rec, field)
                if hasattr(value, "name"):
                    value = value.name
                if value:
                    parts.append(str(value))
            rec.attributes = " ".join(parts)

    @api.depends("list_price", "real_estate_area")
    def _compute_price_per_sqm(self):
        for rec in self:
            multiplier = (rec.unit_price_id.multiplier if rec.unit_price_id
                          and rec.unit_price_id.multiplier else 0)
            if rec.real_estate_area and multiplier:
                value = ((rec.list_price or 0.0) *
                         (multiplier / 1000000)) / rec.real_estate_area
                # Format: remove .0 if integer, otherwise keep 3 decimals max
                rec.price_per_sqm = f"{round(value, 3):.3f}".rstrip(
                    "0").rstrip(".")
            else:
                rec.price_per_sqm = "0"

    @api.depends("list_price", "currency_id", "unit_price_id")
    def _compute_display_price(self):
        for rec in self:
            currency = rec.currency_id or rec.env.company.currency_id
            raw_amount = rec.list_price or 0.0
            if raw_amount % 1:
                amount = f"{round(raw_amount, 3):.3f}".rstrip("0").rstrip(".")
            else:
                amount = str(int(raw_amount))
            unit_name = (rec.unit_price_id.name.lower() if rec.unit_price_id
                         and rec.unit_price_id.name else "-")
            symbol = currency.symbol or "-"
            position = currency.position or ""
            if position == "Before Amount":
                rec.display_price = f"{symbol} {amount} {unit_name}"
            elif position == "After Amount":
                rec.display_price = f"{amount} {unit_name} {symbol}"
            else:
                rec.display_price = f"{amount} {unit_name}"

    # Action
    def action_view_history(self):
        self.ensure_one()
        return {
            "type":
            "ir.actions.act_window",
            "name":
            f"History: {self.name}",
            "res_model":
            "mail.tracking.value",
            "view_mode":
            "list",
            "views": [(self.env.ref("realty_bds.view_product_history_tree").id,
                       "list")],
            "domain": [
                ("mail_message_id.model", "=", "product.template"),
                ("mail_message_id.res_id", "=", self.id),
            ],
            "target":
            "new",
        }

    def action_schedule(self):
        self.ensure_one()  # Ensure only one record is selected
        if self.approval != "approved":
            raise UserError("❌ Error: Wait for approval.")

        # Calculate start (current time) and end (1 hour later)
        start = fields.Datetime.now()
        stop = fields.Datetime.add(start, hours=1)

        # Get the model ID for product.template
        model_id = self.env["ir.model"]._get_id("product.template")

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
                "default_name": f"Meeting: {self.name}",
                "default_start": start,
                "default_stop": stop,
                "default_res_model_id": model_id,  # Link to product.template
                "default_res_id": self.id,  # Current product ID
                "default_user_id":
                self.env.user.id,  # Current user as organizer
                "default_partner_ids": [(6, 0, partner_ids)],  # Attendees
            },
        }

    def action_make_report(self):
        self.ensure_one()
        if self.approval != "approved":
            raise UserError("❌ Error: Wait for approval.")
        # Generate unique report name: Report_<ProductID>_<Timestamp>
        timestamp = fields.Datetime.now().strftime("%Y%m%d%H%M%S")
        report_name = f"Report_{self.id}_{timestamp}"

        return {
            "type": "ir.actions.act_window",
            "name": "Create Product Report",
            "res_model": "product_report",
            "view_mode": "form",
            "view_id":
            self.env.ref("realty_bds.product_report_form_view_user").id,
            "context": {
                "default_product_id": self.id,
                "default_name": report_name,
            },
            "target": "new",
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
            raise UserError(
                "❌ Error: You have exhausted your edit attempts.")
        self.approval = "pending"
        self._assign_moderator_after_send()

    def action_approve(self):
        self.check_action("approve")

        self.approval = "approved"
        self.moderator_id = self.env.user
        self.moderated_on = fields.Datetime.now()

    def action_reject(self):
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
                "default_model_name": self._name,  # Pass the model name
                "default_record_id": self.id,  # Pass the record ID
            },
        }

    def action_remove(self):
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
                "default_model_name": self._name,  # Pass the model name
                "default_record_id": self.id,  # Pass the record ID
            },
        }

    # Helper Method
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

    def format_number(self, value):
        return str(int(value)) if value == int(value) else f"{value:.2f}"

    def _build_address_name(
        self,
        house_number,
        street,
        commune_id,
        district_id,
        real_estate_area,
        usable_area,
        number_of_floors,
        frontage,
        list_price,
        unit_price_id,
    ):
        parts = []
        if house_number:
            parts.append(house_number.strip())
        if street:
            parts.append(street.strip())
        if commune_id:
            parts.append(self.env["commune"].browse(commune_id).name)
        if district_id:
            parts.append(self.env["district"].browse(district_id).name)
        pricestring = ""
        if real_estate_area:
            pricestring = f"{self.format_number(real_estate_area)}"
        else:
            pricestring = "..."
        if usable_area:
            pricestring = pricestring + f"/{self.format_number(usable_area)}"
        else:
            pricestring = pricestring + f"/..."
        parts.append(pricestring)
        if number_of_floors:
            parts.append(f"T{number_of_floors}")
        if frontage:
            parts.append(f"{self.format_number(frontage)}")
        if list_price:
            if unit_price_id:
                parts.append(
                    f"{self.format_number(list_price)}{self.env['unit_price'].browse(unit_price_id).name}"
                )
        return " ".join(parts)

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        # Enforce single record creation since this model work with moderator assignment
        if len(vals_list) > 1:
            raise UserError("Only one record can be created at a time.")
        for vals in vals_list:
            vals["name"] = self._build_address_name(
                vals.get("house_number"),
                vals.get("street"),
                vals.get("commune_id"),
                vals.get("district_id"),
                vals.get("real_estate_area"),
                vals.get("usable_area"),
                vals.get("number_of_floors"),
                vals.get("frontage"),
                vals.get("list_price"),
                vals.get("unit_price_id"),
            )
            vals["company_id"] = self.env.company.id
        records = super().create(vals_list)
        return records

    def write(self, vals):
        self.ensure_one()
        if "name" in vals:
            raise UserError(
                "❌ Error: Direct modification of the 'name' field is not allowed."
            )
        address_keys = {
            "house_number",
            "street",
            "commune_id",
            "district_id",
            "real_estate_area",
            "usable_area",
            "number_of_floors",
            "frontage",
            "list_price",
            "unit_price_id",
        }
        if not (address_keys & set(vals.keys())):
            return super().write(vals)

        vals["name"] = self._build_address_name(
            vals.get("house_number"),
            vals.get("street"),
            vals.get("commune_id"),
            vals.get("district_id"),
            vals.get("real_estate_area"),
            vals.get("usable_area"),
            vals.get("number_of_floors"),
            vals.get("frontage"),
            vals.get("list_price"),
            vals.get("unit_price_id"),
        )
        return super().write(vals)

    def unlink(self):
        # collect attachments before deleting (so we know which records were involved)
        attachments = self.mapped("img_ids")
        rec_ids = self.ids[:]
        model_name = self._name

        # delete the records (this removes the M2M relation rows)
        res = super().unlink()

        # clear res_model/res_id for attachments that pointed to those records
        attachments_to_mark = attachments.filtered(
            lambda a: a.res_model == model_name and a.res_id in rec_ids)
        # mark them orphaned and clear the res_* so they become 'orphans'
        if attachments_to_mark:
            now = fields.Datetime.now()
            # loop to preserve original res_id per attachment
            for att in attachments_to_mark.sudo():
                # write the orphan metadata, then clear the pointers
                att.write({
                    "orphaned_date": now,
                    "orphaned_from_model": model_name,
                    "orphaned_from_res_id": att.res_id,
                    "res_model": False,
                    "res_id": False,
                })
        return res

    @api.model
    def set_presentation_image(self, ids, attachment_id):
        records = self.browse(ids)
        records.write({"presentation_image_id": attachment_id})
        return True

    # Constraints
    @api.constrains("list_price")
    def _check_price_multiplier(self):
        for rec in self:
            if rec.list_price and rec.list_price * 1000 % 1 != 0:
                raise ValidationError(
                    "❌ Error: The price must be rounded to the nearest million! For example: 0.535 billion VND = 535 million VND."
                )

    @api.constrains("real_estate_area", "usable_area", "frontage",
                    "number_of_floors")
    def _check_numeric_values(self):
        for rec in self:
            if any(value < 0 for value in [
                    rec.real_estate_area,
                    rec.usable_area,
                    rec.frontage,
                    rec.number_of_floors,
            ]):
                raise ValidationError(
                    "❌ Error: All numeric fields must be greater than 0!")

    @api.constrains("house_number", "street")
    def _check_valid_values(self):
        try:
            reserved_words = self.env["policy"].get_reserved_words()
        except KeyError:
            reserved_words = frozenset()
            _logger.warning(
                "The 'policy' model is not available. No reserved words will be checked."
            )
        forbidden = r"@#$%^&*()<>?/|{}[]\!+-=`;:.,~"
        for rec in self:
            # Convert to lowercase to check correctly
            house_number_string = (rec.house_number or "").strip().lower()
            street_string = (rec.street or "").strip().lower()
            if house_number_string == "" or street_string == "":
                raise ValidationError(
                    "❌ Error: House number or street cannot be empty or contain only spaces!"
                )
            else:
                if len(rec.house_number) > 50 or len(rec.street) > 50:
                    raise ValidationError(
                        "❌ Error: House number or street cannot exceed 50 characters!"
                    )
            if any(char in (rec.house_number or "")
                   for char in forbidden) or any(char in (rec.street or "")
                                                 for char in forbidden):
                raise ValidationError(
                    f"❌ Error: House number or street cannot contain special characters ({r'@#$%&*<>?/|{}[]\!+=;:,'})!"
                )
            match_hn = next(
                (w for w in reserved_words if w in house_number_string), None)
            if match_hn:
                raise ValidationError(
                    f"❌ Error: House number contains reserved word: '{match_hn}'!"
                )
            match_s = next((w for w in reserved_words if w in street_string),
                           None)
            if match_s:
                raise ValidationError(
                    f"❌ Error: Street contains reserved word: '{match_s}'!")
