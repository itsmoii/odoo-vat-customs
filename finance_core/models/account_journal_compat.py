from odoo import models, fields


class AccountJournalCompat(models.Model):
    _inherit = 'account.journal'

    # Backward-compatibility aliases for older customizations.
    # In Odoo 16+, the liquidity account is `default_account_id`.
    # These fields are simple aliases so legacy views/code keep working.
    default_debit_account_id = fields.Many2one(
        'account.account',
        string='Default Debit Account',
        related='default_account_id',
        readonly=False,
    )
    default_credit_account_id = fields.Many2one(
        'account.account',
        string='Default Credit Account',
        related='default_account_id',
        readonly=False,
    )

