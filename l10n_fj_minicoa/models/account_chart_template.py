# -*- coding: utf-8 -*-
from odoo import api, models

class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _load(self, template_code=None, company=None, install_demo=False):
        """
        Prevent duplicate Fiji VAT taxes and ensure all standard rates are loaded
        cleanly for Mini Supermarket Fiji. Handles 0%, 9%, 12.5%, and 15%.
        """
        Tax = self.env['account.tax']

        # Detect company
        fiji = company if company and company.exists() else self.env.company
        if not (fiji and fiji.country_id and fiji.country_id.code == 'FJ'):
            # Not Fiji — skip
            return super()._load(template_code=template_code, company=company, install_demo=install_demo)

        # ------------------------------
        # PRE-LOAD SNAPSHOT
        # ------------------------------
        rates = [0.0, 9.0, 12.5, 15.0]
        wanted = []
        for rate in rates:
            wanted += [
                (f"VAT {rate}% (Sales)", rate, 'sale'),
                (f"VAT {rate}% (Purchase)", rate, 'purchase'),
            ]

        pre_snapshot = {}
        for name, amount, use in wanted:
            pre_snapshot[(name, use, amount)] = Tax.search([
                ('company_id', '=', fiji.id),
                ('name', '=', name),
                ('type_tax_use', '=', use),
                ('amount', '=', amount),
            ], order='id asc').ids

        # ------------------------------
        # RUN STANDARD ODOO LOADER
        # ------------------------------
        res = super()._load(template_code=template_code, company=company, install_demo=install_demo)

        # ------------------------------
        # POST-LOAD CLEANUP
        # ------------------------------
        for name, amount, use in wanted:
            all_after = Tax.search([
                ('company_id', '=', fiji.id),
                ('name', '=', name),
                ('type_tax_use', '=', use),
                ('amount', '=', amount),
            ], order='id asc')

            # Keep the pre-existing record or first one created
            keep_ids = pre_snapshot.get((name, use, amount)) or (all_after[:1].ids if all_after else [])
            duplicates = all_after.filtered(lambda t: t.id not in keep_ids)

            if duplicates:
                # Never delete taxes; archive to preserve FK integrity
                duplicates.write({'active': False})

        return res
