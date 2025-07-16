import hashlib
from odoo import http # type: ignore

class HashController(http.Controller):

    @http.route('/compute_hash_img_string', type='json', auth='user')
    def compute_hash(self, salt, data):
        params = http.request.env['ir.config_parameter'].sudo()
        specialSalt = params.get_param('test_bds.specialSalt')
        if not specialSalt:
            raise RuntimeError("special_salt not configured")
        combine = f"{salt}:{data}:{specialSalt}"
        hash_str = hashlib.shake_128(combine.encode('utf-8')).hexdigest(10)
        return {'hash': hash_str}



