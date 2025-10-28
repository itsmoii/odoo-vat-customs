# -*- coding: utf-8 -*-
from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        custom = [f for f in ("x_total_price", "x_price_incl_tax") if f in self._fields]
        return fields_list + custom


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        custom = [f for f in ("x_total_price", "x_price_incl_tax") if f in self._fields]
        return fields_list + custom
