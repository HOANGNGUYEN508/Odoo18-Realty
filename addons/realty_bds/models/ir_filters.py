from odoo import models, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from odoo.http import request  # type: ignore
from odoo.tools.safe_eval import safe_eval  # type: ignore


class IrFilters(models.Model):
    _inherit = "ir.filters"

    # Model Method
    @api.model
    def save_or_override_filter(self, filter_data):
        name = filter_data["name"]
        model_id = filter_data["model_id"]
        # Grab the entire incoming context dict…
        full_ctx = filter_data.get("context", {}) or {}
        # …but extract the domain array first:
        domain = full_ctx.pop("domain", [])
        is_default = filter_data.get("is_default", False)
        user_id = self.env.uid
        # If we’re marking this default, clear old defaults
        if is_default:
            old_defaults = self.search([
                ("model_id", "=", model_id),
                ("user_id", "=", user_id),
                ("is_default", "=", True)
            ])
            old_defaults.write({"is_default": False})
        # Find or create
        existing = self.search(
            [
                ("model_id", "=", model_id),
                ("user_id", "=", user_id),
                ("name", "=", name),
            ],
            limit=1,
        )
        # Now vals splits domain vs context
        vals = {
            "domain": domain,  # native domain field
            "context": full_ctx,  # only min_price/max_price/unit ids here
            "is_default": is_default,
        }
        if existing:
            existing.write(vals)
        else:
            vals.update(
                {
                    "name": name,
                    "model_id": model_id,
                    "user_id": user_id,
                }
            )
            self.create(vals)
        return True

    # Constrains
    @api.constrains("name")
    def _check_name(self):
        # Fetch reserved words dynamically from the policy_list model
        reserved_words = request.env["policy"].sudo().search([]).mapped("name")
        reserved_words = set(
            word.strip().lower() for word in reserved_words
        )  # Normalize
        for record in self:
            clean_name = (
                record.name.strip().lower()
            )  # Convert to lowercase to check correctly
            if not record.name.strip():  # Prevent empty or spaces-only names
                raise ValidationError(
                    "❌ Error: Name cannot be empty or contain only spaces!"
                )
            if len(record.name) > 100:  # Limit name length
                raise ValidationError("❌ Error: Name cannot exceed 100 characters!")
            if any(
                char in record.name for char in r"@#$%&*<>?/|{}[]\\!+=;:,"
            ):  # Block special characters
                raise ValidationError(
                    "❌ Error: Name cannot contain special characters!"
                )
            if clean_name in reserved_words:  # Prevent reserved words
                raise ValidationError(f"❌ Error: Name '{record.name}' is not allowed!")
