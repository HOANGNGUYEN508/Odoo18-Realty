from odoo import models, fields, api, tools  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class PermissionTracker(models.Model):
    _name = "permission_tracker"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Dynamic permission mapping (model -> groups)"

    model_name = fields.Char(
        string="Model Name",
        required=True,
        index=True,
        help="Technical model name, e.g. 'guideline' or 'realty_comment'",
    )

    user_group = fields.Many2one("res.groups", string="User group")
    realty_group = fields.Many2one("res.groups", string="Realty group")
    moderator_group = fields.Many2one("res.groups", string="Moderator group")

    @api.model
    @tools.ormcache("model_name")
    def _get_permission_groups(self, model_name):
        record = self.sudo().search([("model_name", "=", model_name)], limit=1)
        if not record:
            raise ValidationError(
                f"No permission mapping found for model '{model_name}'."
            )

        def _get_xml_id(group):
            if not group:
                return None
            return str(group.get_external_id().get(group.id))

        return {
            "user_group": _get_xml_id(record.user_group),
            "realty_group": _get_xml_id(record.realty_group),
            "moderator_group": _get_xml_id(record.moderator_group),
        }

    def _invalidate_permission_cache_for(self, model_names):
        """Invalidate ormcache entries for the given iterable of model_name strings.

        Tries to clear specific ormcache keys using the decorated function's clear_cache helper.
        If that is not available or fails, falls back to clearing registry caches.
        """
        if not model_names:
            return
        keys = {m for m in model_names if m}  # dedupe & ignore falsy
        if not keys:
            return

        # try targeted invalidation first
        try:
            clear_fn = getattr(self._get_permission_groups, "clear_cache", None)
            if clear_fn:
                # clear the cache for each affected key
                for k in keys:
                    try:
                        clear_fn(self, k)
                    except Exception:
                        # if one key fails, continue to others but mark failure
                        raise
                return
        except Exception:
            # fall-through to registry clear on any failure
            pass

        # fallback: clear whole registry cache (less efficient but safe)
        try:
            registry = getattr(self.env, "registry", None) or self.env.registry
            if hasattr(registry, "clear_caches"):
                registry.clear_caches()
            elif hasattr(registry, "clear_cache"):
                registry.clear_cache()
            else:
                # final fallback to model-level method if present
                try:
                    self.clear_caches()
                except Exception:
                    pass
        except Exception:
            # nothing else to do
            pass

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        model_names = []
        for vals, rec in zip(vals_list, records):
            model_names.append(vals.get("model_name") or rec.model_name)

        self._invalidate_permission_cache_for(model_names)
        return records

    def write(self, vals):
        # if nothing relevant changed, avoid any cache invalidation
        relevant_keys = {"model_name", "user_group", "realty_group", "moderator_group"}
        if not (set(vals.keys()) & relevant_keys):
            return super().write(vals)

        before_names = self.mapped("model_name")

        res = super().write(vals)

        after_names = self.mapped("model_name")

        affected = set(before_names) | set(after_names)
        self._invalidate_permission_cache_for(affected)
        return res

    def unlink(self):
        model_names = self.mapped("model_name")
        res = super().unlink()
        self._invalidate_permission_cache_for(model_names)
        return res

    _sql_constraints = [
        (
            "permission_tracker_model_uniq",
            "unique(model_name)",
            "Mapping for this model already exists.",
        )
    ]
