import base64
import logging
import os
import uuid
from pathlib import Path

import requests

from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.tools import config as odoo_config

_logger = logging.getLogger(__name__)

class TaxCoreClient(models.AbstractModel):
    _name = "taxcore.client"
    _description = "Helper to talk to TaxCore V3"

    def _get_cert_dir(self):
        param_dir = odoo_config.get("taxcore_cert_dir")
        if param_dir:
            base_dir = Path(param_dir)
        else:
            data_dir = odoo_config.get("data_dir") or odoo_config.fallback("data_dir")
            base_dir = Path(data_dir or ".") / "taxcore_certs"
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    @api.model
    def send_invoice_v3(self, invoice):
        company = self.env.company
        config = self.env["frcs.vsdc.config"].search(
            [("company_id", "=", company.id), ("active", "=", True)],
            limit=1,
        )
        if not config:
            raise Exception("FRCS V-SDC configuration not found for this company.")

        if not config.cert_pem or not config.key_pem:
            raise Exception("Certificate not configured correctly for this company.")

        cert_bytes = base64.b64decode(config.cert_pem)
        key_bytes = base64.b64decode(config.key_pem)

        # write to temp files with secure permissions
        pac = config.pac
        url = config.vsdc_url.rstrip("/") + "/api/v3/invoices"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "en-US",
            "PAC": pac,
        }
        invoice = dict(invoice or {})
        invoice.setdefault("PAC", pac)

        base_dir = self._get_cert_dir()
        cert_path = base_dir / f"{company.id}_{uuid.uuid4().hex}_cert.pem"
        key_path = base_dir / f"{company.id}_{uuid.uuid4().hex}_key.pem"

        try:
            cert_path.write_bytes(cert_bytes)
            key_path.write_bytes(key_bytes)

            response = requests.post(
                url,
                json=invoice,
                headers=headers,
                timeout=20,
                cert=(str(cert_path), str(key_path)),
            )
        finally:
            for path in (cert_path, key_path):
                try:
                    path.unlink(missing_ok=True)
                except OSError as unlink_error:
                    _logger.warning("Failed to remove temporary cert file %s: %s", path, unlink_error)

        if not response.ok:
            body = response.text
            _logger.error("TaxCore call failed (%s): %s", response.status_code, body)
            try:
                response.raise_for_status()
            except Exception as e:
                raise UserError(_(f"TaxCore API error ({response.status_code}): {body}")) from e

        return response.json()
