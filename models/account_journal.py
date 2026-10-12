from odoo import models, fields, api, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_poultry_processing_journal = fields.Boolean(
        string='Is Poultry Processing Journal',
        help='Indicates if this journal is used for to record poultry LC operations'
    )