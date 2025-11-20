from odoo import models, fields, api
from odoo.exceptions import UserError
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.serialization import PublicFormat
import base64
from odoo.tools.safe_eval import safe_eval

class FrcsVsdcConfig(models.Model):
    _name = "frcs.vsdc.config"
    _description = "FRCS V-SDC Configuration"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )

    vsdc_url = fields.Char(
        string="V-SDC API URL",
        required=True,
        help="Base URL, e.g. https://vsdc.sandbox.vms.frcs.org.fj"
    )
    pac = fields.Char(
        string="PAC",
        required=True,
    )

    pfx_file = fields.Binary(
        string="PFX Certificate",
        help="Client certificate issued by FRCS (PFX/P12).",
    )
    pfx_filename = fields.Char(string="PFX Filename")

    pfx_password = fields.Char(
        string="PFX Password",
        help="Password provided with the PFX.",
    )

    # Extracted PEM versions (never exposed in UI)
    cert_pem = fields.Binary(string="Certificate (PEM)", readonly=True)
    key_pem = fields.Binary(string="Private Key (PEM)", readonly=True)

    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "company_unique",
            "unique(company_id)",
            "Only one FRCS V-SDC configuration is allowed per company.",
        )
    ]

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._convert_pfx_to_pem()
        return record

    def write(self, vals):
        res = super().write(vals)
        # If PFX or password changed, reconvert
        if "pfx_file" in vals or "pfx_password" in vals:
            for rec in self:
                rec._convert_pfx_to_pem()
        return res

    def _convert_pfx_to_pem(self):
        for rec in self:
            if not rec.pfx_file or not rec.pfx_password:
                continue

            try:
                pfx_bytes = base64.b64decode(rec.pfx_file)
                key, cert, extra_certs = pkcs12.load_key_and_certificates(
                    pfx_bytes,
                    rec.pfx_password.encode("utf-8"),
                )

                cert_pem_bytes = cert.public_bytes(Encoding.PEM)
                key_pem_bytes = key.private_bytes(
                    encoding=Encoding.PEM,
                    format=PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=NoEncryption(),
                )

                rec.cert_pem = base64.b64encode(cert_pem_bytes)
                rec.key_pem = base64.b64encode(key_pem_bytes)

                # Optional: clear password after conversion
                # rec.pfx_password = False

            except Exception as e:
                raise UserError(f"Failed to parse PFX certificate: {e}")

    @api.model
    def action_open_company_settings(self):
        action = self.env.ref("custom_pos.action_frcs_vsdc_config").read()[0]
        config = self.search(
            [("company_id", "=", self.env.company.id)],
            limit=1,
        )
        if config:
            action["res_id"] = config.id
            action["views"] = [
                (self.env.ref("custom_pos.view_frcs_vsdc_config_form").id, "form")
            ]
            action["view_mode"] = "form"
        else:
            action["views"] = [
                (self.env.ref("custom_pos.view_frcs_vsdc_config_list").id, "list"),
                (self.env.ref("custom_pos.view_frcs_vsdc_config_form").id, "form"),
            ]
            action["view_mode"] = "list,form"

        base_ctx = action.get("context") or "{}"
        safe_locals = {
            "uid": self.env.user,
            "user": self.env.user,
        }
        ctx = safe_eval(base_ctx, safe_locals)
        ctx["default_company_id"] = self.env.company.id
        action["context"] = ctx
        action["domain"] = [("company_id", "=", self.env.company.id)]
        return action
