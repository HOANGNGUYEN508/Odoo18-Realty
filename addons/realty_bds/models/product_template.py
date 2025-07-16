from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Attributes
    house_number = fields.Char(required=True, string="House Number", tracking=True)
    street = fields.Char(required=True, string="Street", tracking=True)
    real_estate_area = fields.Float(digits=(6, 3), required=True, string="Real Estate Area (m²)", tracking=True)
    usable_area = fields.Float(digits=(6, 3), required=True, string="Usable Area (m²)", tracking=True)
    number_of_floors = fields.Integer(required=True, string="Number of Floors", tracking=True)
    frontage = fields.Float(digits=(6, 3), required=True, string="Frontage (m)", tracking=True)
    presentation_image_id = fields.Integer(string="Presentation Image", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    # Relationship Attributes
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency', 
        default=lambda self: self.env.company.currency_id.id,
        tracking=True
    )
    region_id = fields.Many2one('region', required=True, string="Region", tracking=True)
    province_id = fields.Many2one('res.country.state', required=True, string="Province", tracking=True)
    commune_id = fields.Many2one('commune', required=True, string="Commune", tracking=True)
    district_id = fields.Many2one('district', required=True, string="District", tracking=True)
    type_id = fields.Many2one('type', required=True, string="Type", tracking=True)
    status_id = fields.Many2one('status', required=True, string="Status", tracking=True)
    land_tittle_id = fields.Many2one('land_tittle', required=True, string="Land Title", tracking=True)
    feature_ids = fields.Many2many('feature', required=True, string="Feature")
    home_direction_id = fields.Many2one('home_direction', string="Direction", tracking=True)  # Not required
    unit_price_id = fields.Many2one('unit_price', required=True, string='Unit Price', tracking=True)
    bds_image_ids = fields.Many2many(
        'ir.attachment', 
        required=True, 
        string="Images", 
        domain="[('mimetype', 'like', 'image/%')]"
    )
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, ondelete='restrict', tracking=True)

    # Compute Attributes
    attributes = fields.Char(compute="_compute_attributes", store=False, string="Attributes")
    price_per_sqm = fields.Char(compute="_compute_price_per_sqm", store=False, string="Million/m²")
    display_price = fields.Char(compute='_compute_display_price', store=False, string='Price')
    absolute_price = fields.Float(compute="_compute_absolute_price", store=True, string="Product True Price")
    address = fields.Char(compute="_compute_address", store=False, string="Address")
    
    @api.depends("house_number", "street", "commune_id", "district_id")
    def _compute_address(self):
        for rec in self:
             rec.address = f"{rec.house_number or ''} {rec.street or ''} {rec.commune_id.name or ''} {rec.district_id.name or ''}"

    @api.depends("list_price", "unit_price_id.multiplier")
    def _compute_absolute_price(self):
        for rec in self:
            rec.absolute_price = (rec.list_price or 0.0) * (rec.unit_price_id.multiplier or 1)

    @api.depends('real_estate_area', 'usable_area', 'number_of_floors', 'frontage', 'home_direction_id')
    def _compute_attributes(self):
        for rec in self:
            parts = []
            # Handle float fields with formatting
            for field in ['real_estate_area', 'usable_area', 'frontage']:
                value = getattr(rec, field)
                if value:
                    formatted = round(value, 3) if value % 1 else int(value)
                    parts.append(str(formatted))
            # Handle other fields (int, m2o)
            for field in ['number_of_floors', 'home_direction_id']:
                value = getattr(rec, field)
                if hasattr(value, 'name'):
                    value = value.name
                if value:
                    parts.append(str(value))
            rec.attributes = ' '.join(parts)

    @api.depends('list_price', 'real_estate_area')
    def _compute_price_per_sqm(self):
        for rec in self:
            multiplier = rec.unit_price_id.multiplier if rec.unit_price_id and rec.unit_price_id.multiplier else 0
            if rec.real_estate_area and multiplier:
                value = ((rec.list_price or 0.0) *
                         (multiplier / 1000000)) / rec.real_estate_area
                # Format: remove .0 if integer, otherwise keep 3 decimals max
                rec.price_per_sqm = f"{round(value, 3):.3f}".rstrip(
                    '0').rstrip('.')
            else:
                rec.price_per_sqm = "0"

    @api.depends('list_price', 'currency_id', 'unit_price_id')
    def _compute_display_price(self):
        for rec in self:
            currency = rec.currency_id or rec.env.company.currency_id
            raw_amount = rec.list_price or 0.0
            if raw_amount % 1:
                amount = f"{round(raw_amount, 3):.3f}".rstrip('0').rstrip('.')
            else:
                amount = str(int(raw_amount))
            unit_name = rec.unit_price_id.name.lower(
            ) if rec.unit_price_id and rec.unit_price_id.name else '-'
            symbol = currency.symbol or '-'
            position = currency.position or ''
            if position == 'Before Amount':
                rec.display_price = f"{symbol} {amount} {unit_name}"
            elif position == 'After Amount':
                rec.display_price = f"{amount} {unit_name} {symbol}"
            else:
                rec.display_price = f"{amount} {unit_name}"

    # Action
    def action_view_history(self):
        return {}

    def action_schedule(self):
        return {}

    def action_make_report(self):
        return {}

    def action_test(self):
        return {}

    def action_view_detail(self):
        return {}

    # Helper Method
    def format_number(value):
        return str(int(value)) if value == int(value) else f"{value:.2f}"
    
    def _build_address_name(self, house_number, street, commune_id, district_id, real_estate_area, usable_area, number_of_floors, frontage, list_price, unit_price_id, create_uid):
        parts = []
        if house_number: parts.append(house_number.strip())
        if street: parts.append(street.strip())
        if commune_id: parts.append(self.env['commune'].browse(commune_id).name)
        if district_id: parts.append(self.env['district'].browse(district_id).name)
        pricestring = ""
        if real_estate_area: pricestring = f"{self.format_number(real_estate_area)}"
        else: pricestring = "..."
        if usable_area: pricestring = pricestring + f"/{self.format_number(usable_area)}"
        else: pricestring = pricestring + f"/..."
        parts.append(pricestring)
        if number_of_floors: parts.append(f"T{number_of_floors}")
        if frontage: parts.append(f"{self.format_number(frontage)}")
        if list_price:
            if unit_price_id:
                parts.append(f"{self.format_number(list_price)}{self.env['unit_price'].browse(unit_price_id).name}")               
        if create_uid:
            user = self.env['res.users'].browse(create_uid)
            if user.phone:
                parts.append(f"{user.name}, {user.phone}")
            elif user.mobile:
                parts.append(f"{user.name}, {user.mobile}")
            else : parts.append(f"{user.name}")
        return " ".join(parts)

    # Model Method
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = (
                self._build_address_name(
                    vals.get('house_number'),
                    vals.get('street'),
                    vals.get('commune_id'),
                    vals.get('district_id'),
                    vals.get('real_estate_area'),
                    vals.get('usable_area'),
                    vals.get('number_of_floors'),
                    vals.get('frontage'),
                    vals.get('list_price'),
                    vals.get('unit_price_id'),
                    self.env.uid,
                )
                or vals.get('name')
            )
        records = super().create(vals_list)
        return records

    def write(self, vals):
        address_keys = {
            'house_number',
            'street',
            'commune_id',
            'district_id',
            'real_estate_area',
            'usable_area',
            'number_of_floors',
            'frontage',
            'list_price', 
            'unit_price_id',
        }
        if address_keys & set(vals):
            for rec in self:
                house_number = vals.get('house_number', rec.house_number)
                street = vals.get('street', rec.street)
                commune = vals.get('commune_id', rec.commune_id.id)
                district = vals.get('district_id', rec.district_id.id)
                vals.setdefault('name', False)
                real_estate_area = vals.get('real_estate_area', rec.real_estate_area)
                usable_area = vals.get('usable_area', rec.usable_area)
                number_of_floors = vals.get('number_of_floors', rec.number_of_floors)
                frontage = vals.get('frontage', rec.frontage)
                list_price = vals.get('list_price', rec.list_price)
                unit_price_id = vals.get('unit_price_id', rec.unit_price_id.id)
                create_uid = rec.create_uid.id
                break
            
            vals['name'] = self._build_address_name(
                house_number, 
                street, 
                commune, 
                district, 
                real_estate_area, 
                usable_area, 
                number_of_floors, 
                frontage, 
                list_price,
                unit_price_id,
                create_uid
            )
        return super().write(vals)

    @api.model
    def set_presentation_image(self, ids, attachment_id):
        records = self.browse(ids)
        records.write({'presentation_image_id': attachment_id})
        return True
    
		# Constraints
    @api.constrains('list_price')
    def _check_price_multiplier(self):
        for rec in self:
            if rec.list_price and rec.list_price * 1000 % 1 != 0:
                raise ValidationError(
                    "❌ Error: The price must be rounded to the nearest million! For example: 0.535 billion VND = 535 million VND.")

    @api.constrains('real_estate_area', 'usable_area', 'frontage', 'number_of_floors')
    def _check_valid_values(self):
        for rec in self:
            if any(value < 0 for value in [rec.real_estate_area, rec.usable_area, rec.frontage, rec.number_of_floors]):
                raise ValidationError("❌ Error: All numeric fields must be greater than 0!")

    @api.constrains('house_number', 'street')
    def _check_valid_values(self):
        # Fetch reserved words dynamically from the policy model
        reserved_words = request.env['policy'].sudo().search([]).mapped('name')
        reserved_words = set(word.strip().lower() for word in reserved_words)  # Normalize
        forbidden = r"@#$%^&*()<>?/|{}[]\!+-=`;:.,~"
        for rec in self:
            # Convert to lowercase to check correctly
            house_number_string = (rec.house_number or "").strip().lower()
            street_string = (rec.street or "").strip().lower()
            if house_number_string == "" or street_string == "":
                raise ValidationError("❌ Error: House number or street cannot be empty or contain only spaces!")
            else:
                if len(rec.house_number) > 50 or len(rec.street) > 50:
                    raise ValidationError("❌ Error: House number or street cannot exceed 50 characters!")
            if any(char in (rec.house_number or "") for char in forbidden) or any(char in (rec.street or "") for char in forbidden):
                raise ValidationError("❌ Error: House number or street cannot contain special characters!")
            if house_number_string in reserved_words or street_string in reserved_words:
                raise ValidationError(f"❌ Error: House number or street cannot be used because they contain a prohibited word ({reserved_words})!")