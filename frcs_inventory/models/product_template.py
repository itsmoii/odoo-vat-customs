from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re

# GTIN: allow exactly 8, 12, 13 or 14 digits
_GTIN_RE = re.compile(r"^(?:\d{8}|\d{12}|\d{13}|\d{14})$")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    _sql_constraints = [
        ('frcs_gtin_uniq', 'unique(frcs_gtin)', 'GTIN must be unique among products.'),
        ('x_product_code_uniq', 'unique(x_product_code)', 'Product Code must be unique among products.'),
    ]

    # New fields for custom layout/logic
    x_product_code = fields.Char(string="Product Code", copy=False, index=True,
                                 help="Unique product code.")
    x_product_description = fields.Text(string="Product Description",
                                        help="If empty, receipts will use the product name.")
    x_expiry_date = fields.Date(string="Product Expiry",
                                help="Simple product-level expiry. For lots/serial expiry, use lot-based settings.")

    # Supplier information (simple fields)
    x_supplier_code = fields.Char(string="Supplier Code", size=64)
    x_supplier_name = fields.Char(string="Supplier Name", size=128)
    x_stock_in_date = fields.Date(string="Stock-in Date")
    x_purchase_tax_id = fields.Many2one(
        "account.tax", string="Purchase Tax",
        domain="[('type_tax_use','=','purchase'),('amount_type','=','percent'),('amount','in',[0.0,12.5])]",
        help="Allowed: 0% or 12.5% purchase tax.")
    x_purchase_qty = fields.Integer(string="Product Quantity", default=False)

    # Sales information
    x_sale_tax_id = fields.Many2one(
        "account.tax", string="FRCS Sales Tax",
        domain="[('type_tax_use','=','sale'),('name','ilike','FRCS VAT'),('amount_type','=','percent'),('amount','in',[0.0,12.5])]",
        help="Allowed: FRCS VAT 0% or 12.5% (sales).")
    x_default_discount_amount = fields.Monetary(string="Default Discount",
                                                currency_field="currency_id",
                                                help="Flat discount amount applied by default on POS lines.")

    # New tax selector fields per request
    frcs_tax_id = fields.Many2one(
        "account.tax",
        string="FRCS Tax",
        domain="[('type_tax_use','=','sale'), ('name','ilike','FRCS VAT'), ('amount_type','=','percent'), ('amount','in',[0.0,12.5])]",
        help="Select FRCS VAT (0% or 12.5%) applicable to this product (sales).",
    )
    purchase_tax = fields.Many2one(
        "account.tax",
        string="Purchase Tax",
        domain="[('type_tax_use','=','purchase')]",
        help="Select FRCS VAT for purchases (0% or 12.5%).",
    )

    # Keep existing GTIN but alias it for UI/search consistency
    frcs_gtin = fields.Char(
        string="GTIN",
        help="Global Trade Item Number (8/12/13/14 digits).",
        copy=False,
        index=True,
        tracking=True,
    )
    x_gtin = fields.Char(related="frcs_gtin", string="GTIN", store=True, readonly=False, copy=False)

    # Flags for search filters
    x_is_expired = fields.Boolean(string="Expired", compute="_compute_expiry_flags", store=True)
    x_is_expiring_soon = fields.Boolean(string="Expiring Soon", compute="_compute_expiry_flags", store=True)

    frcs_tax_label = fields.Selection(
        selection=[
            ("A", "A (15%)"),
            ("E", "E (9%)"),
            ("F", "F (0%)"),
            ("P", "P (0.25%)"),
        ],
        string="FRCS Tax Label",
        help="Legacy FRCS label.",
        tracking=True,
    )

    # UI-only helper to display fixed product type label
    x_product_type_label = fields.Char(string="Product Type", compute="_compute_product_type_label")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'type' in fields_list and not res.get('type'):
            # Force default to Goods
            res['type'] = 'product'
        return res

    @api.model
    def create(self, vals):
        # Ensure created products default to Goods
        vals.setdefault('type', 'product')
        return super().create(vals)

    def write(self, vals):
        # Disallow switching away from Goods via UI or API
        if 'type' in vals and vals.get('type') not in (False, 'product'):
            raise ValidationError(_("Only 'Goods' product type is allowed."))
        return super().write(vals)

    @api.constrains("frcs_gtin")
    def _check_frcs_gtin(self):
        for rec in self:
            if rec.frcs_gtin and not _GTIN_RE.match(rec.frcs_gtin):
                raise ValidationError(_("GTIN must be 8, 12, 13 or 14 digits (no spaces or letters)."))
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


class ProductTemplateExt(models.Model):
    _inherit = "product.template"

    @api.constrains("barcode", "frcs_gtin")
    def _check_barcode_matches_gtin(self):
        # Obsolete legacy rule: allow GTIN and Barcode to differ
        return

    @api.constrains("barcode")
    def _check_barcode_unique(self):
        for rec in self:
            if rec.barcode:
                dup = self.search([('barcode', '=', rec.barcode), ('id', '!=', rec.id)], limit=1)
                if dup:
                    raise ValidationError(_("Barcode %s is already used by another product.") % rec.barcode)

    @api.depends('x_expiry_date')
    def _compute_expiry_flags(self):
        from datetime import date, timedelta
        today = date.today()
        soon = today + timedelta(days=30)
        for rec in self:
            rec.x_is_expired = bool(rec.x_expiry_date and rec.x_expiry_date < today)
            rec.x_is_expiring_soon = bool(rec.x_expiry_date and today <= rec.x_expiry_date <= soon)

    @api.onchange('x_expiry_date', 'type')
    def _onchange_x_expiry_date(self):
        if self.x_expiry_date:
            from datetime import date as _date
            if self.x_expiry_date < _date.today():
                return {
                    'warning': {
                        'title': _('Expiry date'),
                        'message': _('Product is past expiry.'),
                    }
                }
        return None

    def _compute_product_type_label(self):
        for rec in self:
            rec.x_product_type_label = _('Goods')
