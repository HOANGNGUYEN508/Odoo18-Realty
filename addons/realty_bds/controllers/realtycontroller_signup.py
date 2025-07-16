from odoo import http # type: ignore
from odoo.http import request # type: ignore

class SignupController(http.Controller):

    @http.route('/web/signup', type='http', auth="public", website=True, methods=["GET", "POST"])
    def web_auth_signup(self, **kw):
        if request.httprequest.method == "POST":
            values = {
                'name': kw.get('name'),
                'email': kw.get('login'), 
                'password': kw.get('password'),
                'phone':kw.get('phone'),
                'citizen_id': kw.get('citizen_id'),
                'province_id': kw.get('province_id'),
                'district_id': kw.get('district_id'),
                'commune_id': kw.get('commune_id'),
                'province_resident_id': kw.get('province_resident_id'),
                'district_resident_id': kw.get('district_resident_id'),
                'commune_resident_id': kw.get('commune_resident_id'),
            }

            # Create partner
            partner = request.env['res.partner'].sudo().create(values)

            # Send a notification to users with the 'realty_bds.access_group_full_users' permission
            request.env['res.partner'].sudo().action_notify_admin_new_partner(partner)

            return request.redirect("/web/login?")

        return request.render("auth_signup.signup")

    @http.route('/get_districts', type='json', auth="public", methods=['POST'])
    def get_districts(self, province_id):
        try:
            province_id = int(province_id) if province_id else False
            if not province_id:
                return {'Error': 'Please choose a valid province/city.'}
            districts = request.env['district'].sudo().search([('province_id', '=', province_id)])
            return {'districts': [{'id': d.id, 'name': d.name} for d in districts]}
        except ValueError:
            return {'Error': 'Invalid province/city ID.'}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/get_communes', type='json', auth="public", methods=['POST'])
    def get_communes(self, district_id):
        try:
            district_id = int(district_id) if district_id else False
            if not district_id:
                return {'Error': 'Please choose a valid district.'}
            communes = request.env['commune'].sudo().search([('district_id', '=', district_id)])
            return {'communes': [{'id': c.id, 'name': c.name} for c in communes]}
        except ValueError:
            return {'Error': 'Invalid districts ID.'}
        except Exception as e:
            return {'error': str(e)}