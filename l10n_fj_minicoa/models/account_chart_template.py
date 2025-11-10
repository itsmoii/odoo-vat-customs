# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import UserError

class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @api.model
    def _load(self, template_code=None, company=None, install_demo=False, force_create=True):
        """
        Prevent duplicate Fiji VAT taxes and ensure all standard rates are loaded
        cleanly for Mini Supermarket Fiji. Handles 0%, 9%, 12.5%, and 15%.
        """
        Tax = self.env['account.tax']
        Journal = self.env['account.journal']
        PosPaymentModel = self.env.get('pos.payment.method')
        TaxGroup = self.env['account.tax.group']
        Imd = self.env['ir.model.data'].sudo()

        # Detect company
        fiji = company if company and company.exists() else self.env.company
        if not (fiji and fiji.country_id and fiji.country_id.code == 'FJ'):
            # Not Fiji — skip
            return super()._load(template_code=template_code, company=company, install_demo=install_demo, force_create=force_create,)

        # ------------------------------
        # TAX GROUP SAFEGUARD
        # ------------------------------
        xmlid_rec = Imd.search([('module', '=', 'l10n_fj_minicoa'), ('name', '=', 'tax_group_vat')], limit=1)
        original_group_id = xmlid_rec.res_id if xmlid_rec else False
        template_group = TaxGroup.browse(original_group_id) if original_group_id else TaxGroup.browse()
        fj_country = self.env.ref('base.fj', raise_if_not_found=False)
        target_group = TaxGroup.with_context(active_test=False).search([
            ('name', '=', 'FRCS VAT'),
            ('company_id', '=', fiji.id),
        ], limit=1)
        if not target_group:
            vals = {
                'name': template_group.name or 'FRCS VAT',
                'company_id': fiji.id,
                'country_id': template_group.country_id.id if template_group.country_id else (fj_country.id if fj_country else False),
                'sequence': template_group.sequence or 10,
            }
            target_group = TaxGroup.create(vals)
        swap_xmlid = bool(xmlid_rec and target_group and xmlid_rec.res_id != target_group.id)
        if swap_xmlid:
            xmlid_rec.write({'res_id': target_group.id})

        try:
            # ------------------------------
            # POINT OF SALE SAFEGUARD
            # ------------------------------
            # The base chart loader wipes existing journals if the company has no accounting setup yet.
            # PoS payment methods have a FK on journals, so we temporarily drop their links to avoid the
            # database constraint error triggered when those journals are deleted, and rewire them later.
            pos_links = []
            if PosPaymentModel:
                pos_methods = PosPaymentModel.with_context(active_test=False).search([
                    ('company_id', '=', fiji.id),
                    ('journal_id', '!=', False),
                ])
                for method in pos_methods:
                    pos_links.append({
                        'method_id': method.id,
                        'journal_type': method.journal_id.type,
                        'journal_code': method.journal_id.code,
                    })
                if pos_methods:
                    try:
                        pos_methods.write({'journal_id': False})
                    except UserError as err:
                        raise UserError("Close or validate your open PoS sessions before installing the Fiji localization.\n%s" % err)

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
            res = super()._load(template_code=template_code, company=company, install_demo=install_demo, force_create=force_create,)

            # Rewire PoS payment methods to their journals (or closest equivalent) after the chart reset.
            if pos_links and PosPaymentModel:
                JournalModel = Journal.with_context(active_test=False)
                journal_cache = {}
                for link in pos_links:
                    cache_key = (link['journal_type'], link['journal_code'])
                    journal = journal_cache.get(cache_key)
                    if not journal:
                        domain = [
                            ('company_id', '=', fiji.id),
                            ('type', '=', link['journal_type']),
                        ]
                        journal = JournalModel.search(domain + [('code', '=', link['journal_code'])], limit=1) if link['journal_code'] else Journal.browse()
                        if not journal:
                            journal = JournalModel.search(domain, limit=1)
                        journal_cache[cache_key] = journal
                    if journal:
                        PosPaymentModel.browse(link['method_id']).write({'journal_id': journal.id})

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
        finally:
            if swap_xmlid:
                xmlid_rec.write({'res_id': original_group_id})
