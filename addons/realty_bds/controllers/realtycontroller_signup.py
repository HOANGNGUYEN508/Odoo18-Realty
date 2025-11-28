from odoo import http  # type: ignore
from odoo.http import request  # type: ignore
from odoo.addons.auth_signup.controllers.main import AuthSignupHome  # type: ignore
import base64
import logging

_logger = logging.getLogger(__name__)


class CustomAuthSignupHome(AuthSignupHome):

    def _prepare_signup_values(self, qcontext):
        """Extend to include custom fields"""
        values = super()._prepare_signup_values(qcontext)

        # Add custom fields to signup values
        custom_fields = [
            "citizen_id",
            "phone",
            "province_id",
            "district_id",
            "commune_id",
            "province_resident_id",
            "district_resident_id",
            "commune_resident_id",
            "signup_company_id",
        ]

        for field in custom_fields:
            if field in request.params:
                values[field] = request.params.get(field)

        return values

    def _signup_with_values(self, token, values):
        """Override to handle company assignment and file uploads"""

        # Extract file data before signup
        file_data_list = self._extract_file_data()

        # Extract evaluation fields
        evaluation_fields = {
            "citizen_id": values.pop("citizen_id", False),
            "phone": values.pop("phone", False),
            "province_id": values.pop("province_id", False),
            "district_id": values.pop("district_id", False),
            "commune_id": values.pop("commune_id", False),
            "province_resident_id": values.pop("province_resident_id", False),
            "district_resident_id": values.pop("district_resident_id", False),
            "commune_resident_id": values.pop("commune_resident_id", False),
            "signup_company_id": int(values.pop("signup_company_id", False)),
        }

        # Call parent signup method
        result = super()._signup_with_values(token, values)
        uid = request.session.uid

        # Assign company to the newly created user
        if evaluation_fields["signup_company_id"] and uid:
            try:
                user = request.env["res.users"].sudo().browse(uid)
                if user.exists():
                    user.write(
                        {
                            "company_id": evaluation_fields["signup_company_id"],
                            "company_ids": [
                                (6, 0, [evaluation_fields["signup_company_id"]])
                            ],
                        }
                    )

                    # Update partner with company information
                    if user.partner_id:
                        user.partner_id.write(
                            {"company_id": evaluation_fields["signup_company_id"]}
                        )

                    # Create user evaluation record and get the record
                    user_eval = user.notify_signup_moderator(
                        user_data=evaluation_fields
                    )

                    # Process and attach uploaded files to user_evaluation
                    if file_data_list and user_eval:
                        self._process_uploaded_files(user_eval, file_data_list)

            except Exception as e:
                _logger.error("Failed to assign company to user: %s", str(e))

        return result

    def _extract_file_data(self):
        """Extract multiple file data from request"""
        file_data_list = []

        try:
            # Get all files from the request
            files = request.httprequest.files.getlist("identity_documents")

            if not files:
                _logger.info("No files uploaded during signup")
                return file_data_list

            for uploaded_file in files:
                if uploaded_file and uploaded_file.filename:
                    try:
                        file_content = uploaded_file.read()
                        file_data_list.append(
                            {
                                "filename": uploaded_file.filename,
                                "content": file_content,
                                "content_type": uploaded_file.content_type,
                            }
                        )
                    except Exception as e:
                        _logger.error(
                            "Error reading file %s: %s", uploaded_file.filename, str(e)
                        )

        except Exception as e:
            _logger.error("Error extracting file data: %s", str(e))

        return file_data_list

    def _process_uploaded_files(self, user_eval, file_data_list):
        """
        Create ir.attachment records and link them to user_evaluation.
        Odoo automatically handles filestore storage when you provide 'datas' field.
        """
        if not user_eval or not user_eval.exists():
            _logger.error("user_evaluation record does not exist")
            return

        if not file_data_list:
            _logger.info("No files to process for user_evaluation %s", user_eval.id)
            return

        # Allowed MIME types
        allowed_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
            "application/pdf",
            "application/msword",
        ]

        # Maximum file size (10MB)
        max_size = 10 * 1024 * 1024

        Attachment = request.env["ir.attachment"].sudo()
        created_attachments = []

        for file_data in file_data_list:
            try:
                content = file_data.get("content", b"")
                filename = file_data.get("filename", "file.bin")
                mimetype = file_data.get("content_type", "application/octet-stream")

                # Server-side validation
                if mimetype not in allowed_types:
                    _logger.warning(
                        "Rejected file %s: invalid type %s", filename, mimetype
                    )
                    continue

                # Size check
                if len(content) > max_size:
                    _logger.warning(
                        "Rejected file %s: size %s exceeds limit",
                        filename,
                        len(content),
                    )
                    continue

                # Convert to base64
                b64_content = base64.b64encode(content)

                # Create attachment - Odoo handles filestore automatically
                attach = Attachment.create(
                    {
                        "name": filename,
                        "type": "binary",  # This tells Odoo to store in filestore
                        "datas": b64_content,  # Odoo automatically writes to filestore
                        "mimetype": mimetype,
                        "res_model": "user_evaluation",
                        "res_id": user_eval.id,
                        "public": False,
                    }
                )

                created_attachments.append(attach.id)

            except Exception as e:
                _logger.exception(
                    "Error processing file %s for user_evaluation %s: %s",
                    file_data.get("filename", "unknown"),
                    user_eval.id,
                    str(e),
                )

        # Update the user_evaluation record with the attachment IDs
        # This ensures the One2many relationship is properly established
        if created_attachments:
            try:
                user_eval.write({"document_id": [(6, 0, created_attachments)]})
            except Exception as e:
                _logger.error(
                    "Failed to link attachments to user_evaluation %s: %s",
                    user_eval.id,
                    str(e),
                )

    @http.route("/get_districts", type="json", auth="public", methods=["POST"])
    def get_districts(self, province_id):
        try:
            province_id = int(province_id) if province_id else False
            if not province_id:
                return {"Error": "Please choose a valid province/city."}
            districts = (
                request.env["district"]
                .sudo()
                .search([("province_id", "=", province_id)])
            )
            return {"districts": [{"id": d.id, "name": d.name} for d in districts]}
        except ValueError:
            return {"Error": "Invalid province/city ID."}
        except Exception as e:
            return {"error": str(e)}

    @http.route("/get_communes", type="json", auth="public", methods=["POST"])
    def get_communes(self, district_id):
        try:
            district_id = int(district_id) if district_id else False
            if not district_id:
                return {"Error": "Please choose a valid district."}
            communes = (
                request.env["commune"]
                .sudo()
                .search([("district_id", "=", district_id)])
            )
            return {"communes": [{"id": c.id, "name": c.name} for c in communes]}
        except ValueError:
            return {"Error": "Invalid districts ID."}
        except Exception as e:
            return {"error": str(e)}
