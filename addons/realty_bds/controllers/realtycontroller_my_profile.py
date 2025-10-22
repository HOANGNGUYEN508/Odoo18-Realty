from odoo import http, _  # type: ignore
from odoo.http import request, route  # type: ignore
from odoo.addons.portal.controllers.portal import CustomerPortal  # type: ignore
from odoo.exceptions import AccessDenied, UserError  # type: ignore
import logging

_logger = logging.getLogger(__name__)


class InheritCustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        """Values for /my/* templates rendering.

        Does not include the record counts.
        """
        # get customer sales rep
        sales_user_sudo = request.env["res.users"]
        partner_sudo = request.env.user.partner_id
        if partner_sudo.user_id and not partner_sudo.user_id._is_public():
            sales_user_sudo = partner_sudo.user_id
        else:
            fallback_sales_user = partner_sudo.commercial_partner_id.user_id
            if fallback_sales_user and not fallback_sales_user._is_public():
                sales_user_sudo = fallback_sales_user

        return {
            "sales_user": sales_user_sudo,
            "page_name": "home",
        }

    def _prepare_home_portal_values(self, counters):
        """Values for /my & /my/home routes template rendering.

        Includes the record count for the displayed badges.
        where 'counters' is the list of the displayed badges
        and so the list to compute.
        """
        return {}

    def get_error(e, path=""):
        """Recursively dereferences `path` (a period-separated sequence of dict
        keys) in `e` (an error dict or value), returns the final resolution IIF it's
        an str, otherwise returns None
        """
        for k in path.split(".") if path else []:
            if not isinstance(e, dict):
                return None
            e = e.get(k)

        return e if isinstance(e, str) else None

    def _update_password(self, old, new1, new2):
        for k, v in [("old", old), ("new1", new1), ("new2", new2)]:
            if not v:
                return {
                    "errors": {
                        "password": {k: _("You cannot leave any password empty.")}
                    }
                }

        if new1 != new2:
            return {
                "errors": {
                    "password": {
                        "new2": _(
                            "The new password and its confirmation must be identical."
                        )
                    }
                }
            }

        try:
            request.env["res.users"].change_password(old, new1)
        except AccessDenied as e:
            msg = e.args[0]
            if msg == AccessDenied().args[0]:
                msg = _(
                    "The old password you provided is incorrect, your password was not changed."
                )
            return {"errors": {"password": {"old": msg}}}
        except UserError as e:
            return {"errors": {"password": str(e)}}

        # update session token so the user does not get logged out (cache cleared by passwd change)
        new_token = request.env.user._compute_session_token(request.session.sid)
        request.session.session_token = new_token

        return {"success": {"password": True}}

    @route(["/test12345"], type="json", auth="user", methods=["POST"], csrf=False)
    def test_controller(self):
        _logger.info("This is working as intended")
        return {"result": "ok"}

    @route(
        "/my/security", type="http", auth="user", website=True, methods=["GET", "POST"]
    )
    def security(self, **post):
        # Original method setup
        values = self._prepare_portal_layout_values()
        values["get_error"] = InheritCustomerPortal.get_error
        values["allow_api_keys"] = bool(
            request.env["ir.config_parameter"].sudo().get_param("portal.allow_api_keys")
        )
        values["open_deactivate_modal"] = False

        # Process POST request (password update)
        if request.httprequest.method == "POST":
            # Update values with password change result
            values.update(
                self._update_password(
                    post["old"].strip(), post["new1"].strip(), post["new2"].strip()
                )
            )

        # Check for successful password update
        if "success" in values:
            _logger.info("success in values")
            request.session.update({"password": "changed"})
            InheritCustomerPortal.test_controller(self)
            # Redirect to home on success
            return request.redirect("/my/home")

        # Render the security page if not redirected
        return request.render(
            "portal.portal_my_security",
            values,
            headers={
                "X-Frame-Options": "SAMEORIGIN",
                "Content-Security-Policy": "frame-ancestors 'self'",
            },
        )

    @route(["/my/home"], type="http", auth="user", website=True)
    def home(self, **kw):
        values = self._prepare_portal_layout_values()
        values.update(self._prepare_home_portal_values([]))
        values["user"] = request.env.user
        values["partner"] = request.env.user.partner_id
        values["changed"] = False

        if request.session.get("password") == "changed":
            _logger.info("Debugging")
            values["changed"] = True
            request.session.update({"password": "not changed"})

        return request.render("portal.portal_my_home", values)
