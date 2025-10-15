from odoo import _, fields, models
from odoo.osv import expression


class ProductEnquiryWizard(models.TransientModel):
    _name = "frcs.product.enquiry.wizard"
    _description = "Product Enquiry Wizard"

    item_code = fields.Char(string="Item Code")
    item_name = fields.Char(string="Item Name")
    item_short_description = fields.Char(string="Item Short Description")
    supplier_code = fields.Char(string="Supplier Code")
    product_category_id = fields.Many2one("product.category", string="Product Category")
    product_type = fields.Selection(
        selection=[
            ("product", "Storable Product"),
            ("consu", "Consumable"),
            ("service", "Service"),
        ],
        string="Product Type",
    )

    def action_reset(self):
        self.ensure_one()
        self.write({
            "item_code": False,
            "item_name": False,
            "item_short_description": False,
            "supplier_code": False,
            "product_category_id": False,
            "product_type": False,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "name": _("Product Enquiry"),
        }

    def action_search(self):
        self.ensure_one()
        domain_parts = []

        if self.item_code:
            domain_parts.append([("default_code", "ilike", self.item_code)])

        if self.item_name:
            domain_parts.append([("name", "ilike", self.item_name)])

        if self.item_short_description:
            term = self.item_short_description
            domain_parts.append([
                "|",
                ("description_sale", "ilike", term),
                ("name", "ilike", term),
            ])

        if self.product_category_id:
            domain_parts.append([("categ_id", "=", self.product_category_id.id)])

        if self.product_type:
            domain_parts.append([("type", "=", self.product_type)])

        if self.supplier_code:
            supplier_records = self.env["product.supplierinfo"].sudo().search(
                [("product_code", "ilike", self.supplier_code)]
            )
            template_ids = supplier_records.mapped("product_tmpl_id").ids
            domain_parts.append([("id", "in", template_ids or [0])])

        domain = expression.AND(domain_parts) if domain_parts else []
        products = self.env["product.template"].sudo().search(domain)

        return {
            "type": "ir.actions.act_window",
            "name": "Product Enquiry Results",
            "res_model": "product.template",
            "view_mode": "list,kanban,form",
            "domain": [("id", "in", products.ids)],
            "context": {"search_default_active": 1},
        }
