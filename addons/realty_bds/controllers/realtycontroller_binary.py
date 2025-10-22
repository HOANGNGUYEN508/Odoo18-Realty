# controllers/reality_binary.py
import base64
import logging
import time

from odoo import http  # type: ignore
from odoo.http import request  # type: ignore
from odoo.exceptions import AccessError, UserError  # type: ignore
from odoo.tools import str2bool  # type: ignore
from odoo.tools.image import image_guess_size_from_field_name  # type: ignore

_logger = logging.getLogger(__name__)

ALLOWED_ATTACHMENT_FIELDS = {
    "product.template": ["img_ids"],
    "res.users": ["avatar_128"],
    "notification": ["img_ids"],
    "guideline": ["img_ids"],
    "congratulation": ["img_ids"],
}

# Toggle: allow attachment creators to pass fast-path immediately (useful for unsaved parent record previews)
ALLOW_OWNER_FASTPATH = True


class AttachmentSecurityService:
    """Service class for attachment security checks to avoid DRY violations."""

    @staticmethod
    def is_model_field_allowed(model, field):
        allowed = ALLOWED_ATTACHMENT_FIELDS.get(model)
        return allowed and field in allowed

    @staticmethod
    def check_fast_path_access(env, attachment_id, model, field):
        """
        Check fast-path access for a single attachment.
        Returns True if the client-supplied fast-path specifically passes.
        Only logs warnings for access-denied situations and exceptions.
        """
        try:
            attachment_id = int(attachment_id) if attachment_id is not None else None
        except Exception:
            return False

        if not model or not field:
            return False

        if not AttachmentSecurityService.is_model_field_allowed(model, field):
            return False

        # Quick read: check public / creator info so we can optionally allow uploader
        try:
            att_infos = env["ir.attachment"].sudo().browse([attachment_id]).read(["id", "create_uid", "public"])
            att_info = att_infos[0] if att_infos else {}
            create_uid = att_info.get("create_uid") and att_info["create_uid"][0]
            is_public = bool(att_info.get("public"))
            if is_public:
                return True
            if ALLOW_OWNER_FASTPATH and create_uid == env.uid:
                return True
        except Exception:
            _logger.exception("Fast-path(single): failed to read basic attachment info for %s", attachment_id)

        # Proceed with model search
        try:
            model_env_for_search = env[model].sudo()
        except Exception:
            return False

        try:
            domain = [(field, "in", [attachment_id])]
            recs = model_env_for_search.search(domain, limit=1)
        except Exception:
            _logger.exception(
                "Fast-path(single) search error on %s.%s for attachment %s", model, field, attachment_id
            )
            return False

        for rec in recs:
            try:
                env[model].browse(int(rec.id)).check_access("read")
            except AccessError:
                # do not spam logs — warning only when entirely failing higher-level checks
                continue
            except Exception:
                _logger.exception("Fast-path(single): unexpected error checking %s id=%s", model, rec.id)
                continue
            else:
                return True

        return False

    @staticmethod
    def batch_check_fast_path_access(env, attachment_ids, model, field):
        """
        Batch-optimized fast-path check for multiple attachments.
        Returns set of attachment IDs that pass the fast-path check.
        Only logs exceptions and warnings.
        """
        if not model or not field:
            return set()

        if not AttachmentSecurityService.is_model_field_allowed(model, field):
            return set()

        try:
            model_env_for_search = env[model].sudo()
        except Exception:
            _logger.exception("Batch fast-path: unknown model %s", model)
            return set()

        allowed_attachment_ids = set()
        try:
            infos = env["ir.attachment"].sudo().browse(list(attachment_ids)).read(["id", "create_uid", "public"])
            for info in infos:
                aid = int(info.get("id"))
                is_public = bool(info.get("public"))
                create_uid = info.get("create_uid") and info["create_uid"][0]
                if is_public:
                    allowed_attachment_ids.add(aid)
                elif ALLOW_OWNER_FASTPATH and create_uid == env.uid:
                    allowed_attachment_ids.add(aid)
        except Exception:
            _logger.exception("Batch fast-path: failed reading base attachment infos; will continue to full search")

        remaining_to_search = [aid for aid in attachment_ids if int(aid) not in allowed_attachment_ids]
        if not remaining_to_search:
            return allowed_attachment_ids

        try:
            recs = model_env_for_search.search([(field, "in", remaining_to_search)])
        except Exception:
            _logger.exception(
                "Batch fast-path: search error on %s.%s for ids %s", model, field, remaining_to_search
            )
            return allowed_attachment_ids

        if not recs:
            return allowed_attachment_ids

        for rec in recs:
            try:
                env[model].browse(int(rec.id)).check_access("read")
            except AccessError:
                continue
            except Exception:
                _logger.exception("Batch fast-path: unexpected error while checking rec %s id=%s", model, rec.id)
                continue

            # record is readable by current user — extract referenced attachment ids
            ref_ids = []
            try:
                ref_field = getattr(rec, field)
                ref_ids = ref_field.ids if hasattr(ref_field, "ids") else list(ref_field)
            except Exception:
                try:
                    data = rec.read([field])[0].get(field, []) or []
                    ref_ids = [int(x) for x in data]
                except Exception:
                    _logger.exception("Batch fast-path: failed to extract references from %s id=%s", model, rec.id)
                    continue

            for aid in ref_ids:
                if aid in remaining_to_search:
                    allowed_attachment_ids.add(int(aid))

        return allowed_attachment_ids


class BinaryController(http.Controller):
    """
    Protected binary/image controller with optional safe narrowing by client-supplied model/field,
    but only if the server-side allowlist accepts them.
    """

    def _ensure_user_can_read_linked_record(
        self, attachment, allow_any=True, model_whitelist=None, field_whitelist=None
    ):
        """
        Grant access if:
          - attachment.public True
          - OR direct attachment.res_model/res_id pointing to a readable record
          - OR fallback: any stored m2m field referencing this attachment has at least one readable record
        Only warnings/exceptions are logged.
        """

        if getattr(attachment, "public", False):
            return

        # DIRECT res_model/res_id path
        res_model = getattr(attachment, "res_model", False)
        res_id = getattr(attachment, "res_id", False)
        if res_model and res_id:
            try:
                related_model = request.env[res_model]
                related = related_model.browse(int(res_id))
                try:
                    related.check_access("read")
                except AccessError:
                    pass
                else:
                    return
            except Exception:
                _logger.exception("Direct fast-path: unexpected error checking %s id=%s", res_model, res_id)

        # FALLBACK: scan stored many2many fields that point to ir.attachment
        domain = [
            ("ttype", "=", "many2many"),
            ("relation", "=", "ir.attachment"),
            ("store", "=", True),
        ]
        if model_whitelist:
            domain.append(("model", "in", list(model_whitelist)))
        if field_whitelist:
            domain.append(("name", "in", list(field_whitelist)))

        mm_fields = request.env["ir.model.fields"].sudo().search(domain)
        if not mm_fields:
            _logger.warning("No stored m2m fields pointing to ir.attachment found (attachment %s)", attachment.id)
            raise AccessError("You are not allowed to access this file.")

        found_any_reference = False
        unreadable_refs = []
        for f in mm_fields:
            model_name = f.model
            field_name = f.name
            try:
                search_env = request.env[model_name].sudo()
            except Exception:
                continue

            try:
                rec = search_env.search([(field_name, "in", int(attachment.id))], limit=1)
            except Exception:
                _logger.exception("Error searching %s.%s for attachment %s", model_name, field_name, attachment.id)
                continue

            if not rec:
                continue

            found_any_reference = True
            try:
                request.env[model_name].browse(int(rec.id)).check_access("read")
            except AccessError as ae:
                unreadable_refs.append((model_name, rec.id))
                if not allow_any:
                    _logger.warning("User cannot read referenced %s id=%s for attachment %s: %s", model_name, rec.id, attachment.id, ae)
                    raise AccessError("You are not allowed to access this file.")
                continue
            except Exception:
                _logger.exception("Unexpected error checking access on %s id=%s", model_name, rec.id)
                if not allow_any:
                    raise AccessError("You are not allowed to access this file.")
                continue
            else:
                if allow_any:
                    return

        if not found_any_reference:
            _logger.warning("Found no references to attachment %s (res_model/res_id empty and no m2m refs)", attachment.id)
            raise AccessError("You are not allowed to access this file.")

        _logger.warning("Found references but none readable for attachment %s unreadable_refs=%s", attachment.id, unreadable_refs)
        raise AccessError("You are not allowed to access this file.")

    def _serve_direct_binary(self, attachment, filename=None, download=False):
        """Serve binary data directly, completely bypassing ORM security."""
        if getattr(attachment, "datas", False):
            file_data = base64.b64decode(attachment.datas)

            headers = [
                ("Content-Type", attachment.mimetype or "application/octet-stream"),
                ("Content-Length", len(file_data)),
            ]
            if download:
                headers.append(("Content-Disposition", f'attachment; filename={filename or attachment.name}'))

            return request.make_response(file_data, headers)
        else:
            raise request.not_found()

    @http.route(
        ["/web/content_protected/<int:attachment_id>"],
        type="http",
        auth="public",
        readonly=True,
    )
    def content_protected(
        self,
        attachment_id,
        filename=None,
        download=False,
        nocache=False,
        access_token=None,
        model=None,
        field=None,
    ):
        """
        Serve an ir.attachment if public OR if the current user can read the linked record.
        Uses the fast-path check when appropriate to serve a direct binary response.
        Only warnings and exceptions are logged.
        """
        try:
            Attachment = request.env["ir.attachment"].sudo()
            attachment = Attachment.browse(int(attachment_id))
            if not attachment.exists():
                raise request.not_found()

            model_param = model or request.httprequest.args.get("model")
            field_param = field or request.httprequest.args.get("field")

            if access_token:
                record = request.env["ir.binary"]._find_record(None, "ir.attachment", int(attachment_id), access_token, field="raw")
                stream = request.env["ir.binary"]._get_stream_from(record, "raw", filename)
                send_file_kwargs = {"as_attachment": str2bool(download)}
                if nocache:
                    send_file_kwargs["max_age"] = None
                return stream.get_response(**send_file_kwargs)

            fast_path_allowed = AttachmentSecurityService.check_fast_path_access(
                request.env, attachment_id, model_param, field_param
            )

            if fast_path_allowed:
                return self._serve_direct_binary(attachment, filename, download)
            else:
                model_whitelist = (
                    [model_param] if model_param and AttachmentSecurityService.is_model_field_allowed(model_param, field_param) else None
                )
                field_whitelist = (
                    [field_param] if field_param and AttachmentSecurityService.is_model_field_allowed(model_param, field_param) else None
                )
                self._ensure_user_can_read_linked_record(
                    attachment, model_whitelist=model_whitelist, field_whitelist=field_whitelist
                )

                stream = request.env["ir.binary"].sudo()._get_stream_from(attachment.sudo(), "raw", filename)
                send_file_kwargs = {"as_attachment": str2bool(download)}
                if nocache:
                    send_file_kwargs["max_age"] = None

                return stream.get_response(**send_file_kwargs)

        except AccessError:
            _logger.warning("content_protected: AccessError for attachment %s (uid=%s)", attachment_id, request.env.uid)
            raise AccessError("You are not allowed to access this file.")
        except Exception:
            _logger.exception("content_protected: Failed to serve protected attachment %s", attachment_id)
            raise request.not_found()

    @http.route(
        [
            "/web/image_protected",
            "/web/image_protected/<string:xmlid>",
            "/web/image_protected/<string:xmlid>/<string:filename>",
        ],
        type="http",
        auth="public",
        readonly=True,
    )
    def image_protected(
        self,
        xmlid=None,
        model="ir.attachment",
        id=None,
        field="raw",
        filename_field="name",
        filename=None,
        mimetype=None,
        width=0,
        height=0,
        crop=False,
        access_token=None,
        download=False,
        nocache=False,
    ):
        """
        Mirrors /web/image semantics but enforces read access for the current user on the referenced record.
        Only warnings and exceptions are logged.
        """
        try:
            if xmlid or access_token:
                record = request.env["ir.binary"]._find_record(xmlid, model, id and int(id), access_token, field=field)
            else:
                try:
                    model_env = request.env[model].sudo()
                except Exception:
                    raise request.not_found()
                record = model_env.browse(int(id))

                if record._name == "ir.attachment":
                    self._ensure_user_can_read_linked_record(record)
                else:
                    record.check_access("read")

            try:
                stream = (
                    request.env["ir.binary"]
                    .sudo()
                    ._get_image_stream_from(
                        record,
                        field,
                        filename=filename,
                        filename_field=filename_field,
                        mimetype=mimetype,
                        width=int(width),
                        height=int(height),
                        crop=crop,
                    )
                )
            except UserError:
                if (int(width), int(height)) == (0, 0):
                    width, height = image_guess_size_from_field_name(field)
                placeholder = request.env.ref("web.image_placeholder").sudo()
                stream = (
                    request.env["ir.binary"]
                    .sudo()
                    ._get_image_stream_from(placeholder, "raw", width=int(width), height=int(height), crop=crop)
                )
                stream.public = False

            if request.httprequest.args.get("access_token"):
                stream.public = True

        except AccessError:
            _logger.warning("image_protected: AccessError for image %s/%s (uid=%s)", model, id, request.env.uid)
            raise AccessError("You are not allowed to access this image.")
        except Exception:
            _logger.exception("Failed to serve protected image %s/%s", model, id)
            raise request.not_found()

        send_file_kwargs = {"as_attachment": str2bool(download)}
        if nocache:
            send_file_kwargs["max_age"] = None

        return stream.get_response(**send_file_kwargs)


class AttachmentMetaFastpathController(http.Controller):
    @http.route("/realty/attachment/meta_fastpath", type="json", auth="user")
    def attachment_meta_fastpath(self, attachment_ids, model=None, field=None):
        """
        Batch-optimized fast-path-only metadata endpoint.

        Returns a mapping {attachment_id: {id, name, mimetype}} for attachment ids
        where the client-supplied fast-path check passes.
        Only exceptions and warnings are logged.
        """
        result = {}
        Attachment = request.env["ir.attachment"]

        try:
            ids = [int(i) for i in attachment_ids] if attachment_ids else []
        except Exception:
            _logger.exception("attachment_meta_fastpath: invalid attachment_ids input")
            return result

        if not ids:
            return result

        allowed_attachment_ids = AttachmentSecurityService.batch_check_fast_path_access(request.env, ids, model, field)

        if not allowed_attachment_ids:
            return result

        try:
            metas = Attachment.sudo().browse(list(allowed_attachment_ids)).read(["id", "name", "mimetype"])
            for m in metas:
                result[int(m["id"])] = {"id": int(m["id"]), "name": m.get("name", ""), "mimetype": m.get("mimetype", "")}
        except Exception:
            _logger.exception(
                "attachment_meta_fastpath: failed to read attachment metadata for ids %s",
                list(allowed_attachment_ids),
            )

        return result