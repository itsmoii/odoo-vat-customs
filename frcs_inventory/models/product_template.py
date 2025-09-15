from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re

_GTIN_RE = re.compile(r"^\d{8,14}$")  # simple GTIN 8-14 digits check


class ProductTemplate(models.Model):
    _inherit = "product.template"

    _sql_constraints = [
        ('frcs_gtin_uniq', 'unique(frcs_gtin)', 'GTIN must be unique among products.'),
    ]

    frcs_gtin = fields.Char(
        string="GTIN",
        help="Global Trade Item Number (8-14 digits).",
        copy=False,
        index=True,
        tracking=True,
    )

    frcs_tax_label = fields.Selection(
        selection=[
            ("A", "A (15%)"),
            ("E", "E (9%)"),
            ("F", "F (0%)"),
            ("P", "P (0.25%)"),
        ],
        string="FRCS Tax Label",
        help="Required FRCS VAT code printed on fiscal documents.",
        tracking=True,
    )

    @api.constrains("frcs_gtin")
    def _check_frcs_gtin(self):
        for rec in self:
            if rec.frcs_gtin and not _GTIN_RE.match(rec.frcs_gtin):
                raise ValidationError(_("GTIN must be 8 to 14 digits (no spaces or letters)."))
            if rec.frcs_gtin:
                #Check for uniqueness across products (simple check)
                dup = self.search([("frcs_gtin", "=", rec.frcs_gtin), ("id", "!=", rec.id)], limit=1)
                if dup:
                    raise ValidationError(_("GTIN %s is already used by another product.") % rec.frcs_gtin)
    
    @api.constrains("barcode", "frcs_gtin")
    def _check_barcode_matches_gtin(self):
        """
        If barcode is present AND is purely 8–14 digits (i.e., looks like a GTIN),
        then it must match frcs_gtin to avoid mismatches during POS scanning & fiscalization.
        """
        for rec in self:
            if rec.barcode and _GTIN_RE.match(rec.barcode):
                if not rec.frcs_gtin:
                    raise ValidationError(_("Barcode looks like a GTIN, but GTIN field is empty. Please set GTIN to match the barcode."))
                if rec.barcode != rec.frcs_gtin:
                    raise ValidationError(_("Barcode (%s) looks like a GTIN and must equal GTIN (%s).") % (rec.barcode, rec.frcs_gtin))

    @api.onchange("frcs_gtin")
    def _onchange_frcs_gtin_fill_barcode(self):
        """If barcode is empty and GTIN is set/valid, use it as barcode for convenience."""
        for rec in self:
            if rec.frcs_gtin and _GTIN_RE.match(rec.frcs_gtin) and not rec.barcode:
                rec.barcode = rec.frcs_gtin