from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore


class Province(models.Model):
    _inherit = "res.country.state"
    _description = "Province/City"
    _order = "sort_key asc"  # Use sort_key field for sorting

    # Attributes
    active = fields.Boolean(string="Active", default=True)
    sort_key = fields.Char(
        string="Sort Key", compute="_compute_sort_key", store=True, index=True
    )  # Computed field to store Vietnamese alphabet sort key

    # Relationship Attributes
    district_ids = fields.One2many("district", "province_id", string="District List")

    # Model method
    @api.model
    def _domain_vietnam_states(self):
        vietnam = self.env["res.country"].search([("code", "=", "VN")], limit=1)
        return [("country_id", "=", vietnam.id)] if vietnam else []

    # Depends
    @api.depends("name")
    def _compute_sort_key(self):
        """Generate sort key based on Vietnamese alphabetical order."""
        vietnamese_order = {
            "a": "a",
            "à": "a1",
            "á": "a2",
            "ả": "a3",
            "ã": "a4",
            "ạ": "a5",
            "ă": "a6",
            "ằ": "a7",
            "ắ": "a8",
            "ẳ": "a9",
            "ẵ": "a10",
            "ặ": "a11",
            "â": "a12",
            "ầ": "a13",
            "ấ": "a14",
            "ẩ": "a15",
            "ẫ": "a16",
            "ậ": "a17",
            "d": "d",
            "đ": "d1",
            "e": "e",
            "è": "e1",
            "é": "e2",
            "ẻ": "e3",
            "ẽ": "e4",
            "ẹ": "e5",
            "ê": "e6",
            "ề": "e7",
            "ế": "e8",
            "ể": "e9",
            "ễ": "e10",
            "ệ": "e11",
            "i": "i",
            "ì": "i1",
            "í": "i2",
            "ỉ": "i3",
            "ĩ": "i4",
            "ị": "i5",
            "o": "o",
            "ò": "o1",
            "ó": "o2",
            "ỏ": "o3",
            "õ": "o4",
            "ọ": "o5",
            "ô": "o6",
            "ồ": "o7",
            "ố": "o8",
            "ổ": "o9",
            "ỗ": "o10",
            "ộ": "o11",
            "ơ": "o12",
            "ờ": "o13",
            "ớ": "o14",
            "ở": "o15",
            "ỡ": "o16",
            "ợ": "o17",
            "u": "u",
            "ù": "u1",
            "ú": "u2",
            "ủ": "u3",
            "ũ": "u4",
            "ụ": "u5",
            "ư": "u6",
            "ừ": "u7",
            "ứ": "u8",
            "ử": "u9",
            "ữ": "u10",
            "ự": "u11",
            "y": "y",
            "ỳ": "y1",
            "ý": "y2",
            "ỷ": "y3",
            "ỹ": "y4",
            "ỵ": "y5",
        }

        for record in self:
            if (
                not record.name
            ):  # If the name field is empty (None or ''), set sort_key to an empty string
                record.sort_key = ""
                continue

            # Convert name to lowercase for consistent processing
            name = record.name.lower()

            sort_key = ""
            for char in name:
                # Replace Vietnamese characters with their sort values
                if char in vietnamese_order:
                    sort_key += vietnamese_order[char]
                else:
                    # Keep non-Vietnamese characters as is
                    sort_key += char
            record.sort_key = sort_key

    # Constrain
    _sql_constraints = [
        (
            "province_unique_name",
            "UNIQUE(name,region_id)",
            "This name already exists!",
        ),  # Ensure uniqueness
    ]
