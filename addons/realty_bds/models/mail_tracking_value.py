from odoo import api, fields, models  # type: ignore


class MailTrackingValue(models.Model):
    _inherit = "mail.tracking.value"

    # Compute Attributes
    display_history = fields.Char(
        string="History",
        compute="_compute_display_history",
        store=False,
    )

    @api.depends(
        "create_uid",
        "create_date",
        "old_value_char",
        "new_value_char",
        "old_value_text",
        "new_value_text",
        "old_value_integer",
        "new_value_integer",
        "old_value_float",
        "new_value_float",
        "old_value_datetime",
        "new_value_datetime",
        "field_id",
    )
    def _compute_display_history(self):
        fmt = "%b %d, %I:%M %p"
        for rec in self:
            # 1) author
            author = rec.create_uid.name or "System"

            # 2) timestamp in user timezone
            if rec.create_date:
                dt = fields.Datetime.context_timestamp(rec, rec.create_date)
                date_str = dt.strftime(fmt).lstrip("0").replace(" 0", " ")
            else:
                date_str = "Unknown"

            # 3) determine technical field type
            ttype = rec.field_id.ttype if rec.field_id else "char"

            # 4) fetch formatted old & new with Odoo helper
            old_vals = rec._format_display_value(ttype, new=False)
            new_vals = rec._format_display_value(ttype, new=True)
            # get first entry (there’s always one)
            old = old_vals[0] or ""
            new = new_vals[0] or ""

            # 5) human‑readable field label
            label = rec.field_id.field_description or rec.field_id.name or ""

            # 6) assemble our one‑liner
            rec.display_history = f"{date_str} - [{author}]: {old} -> {new}({label})"
