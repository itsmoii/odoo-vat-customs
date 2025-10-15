from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    finance_pos_eod_journal_id = fields.Many2one('account.journal', string='POS EOD Journal', domain="[('type','=','general')]")
    finance_pos_revenue_account_id = fields.Many2one('account.account', string='Revenue Account')
    finance_pos_vat_account_id = fields.Many2one('account.account', string='VAT Payable Account')
    finance_pos_clearing_account_id = fields.Many2one('account.account', string='Clearing Account')
    finance_auto_bill_on_receipt = fields.Boolean(string='Auto-create Vendor Bill on Receipt')

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('finance_core.pos_eod_journal_id', self.finance_pos_eod_journal_id.id or False)
        ICP.set_param('finance_core.pos_revenue_account_id', self.finance_pos_revenue_account_id.id or False)
        ICP.set_param('finance_core.pos_vat_account_id', self.finance_pos_vat_account_id.id or False)
        ICP.set_param('finance_core.pos_clearing_account_id', self.finance_pos_clearing_account_id.id or False)
        ICP.set_param('finance_core.auto_bill_on_receipt', bool(self.finance_auto_bill_on_receipt))

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            finance_pos_eod_journal_id=int(ICP.get_param('finance_core.pos_eod_journal_id') or 0) or False,
            finance_pos_revenue_account_id=int(ICP.get_param('finance_core.pos_revenue_account_id') or 0) or False,
            finance_pos_vat_account_id=int(ICP.get_param('finance_core.pos_vat_account_id') or 0) or False,
            finance_pos_clearing_account_id=int(ICP.get_param('finance_core.pos_clearing_account_id') or 0) or False,
            finance_auto_bill_on_receipt=ICP.get_param('finance_core.auto_bill_on_receipt') == 'True',
        )
        return res

