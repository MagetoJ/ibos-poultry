# -*- coding: utf-8 -*-
from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    cost_share = fields.Float(
        string='Cost Share (%)',
        digits=(5, 2),
        help='Percentage of total manufacturing cost allocated to this byproduct. '
             'Used in poultry processing to distribute costs among main product and byproducts.'
    )
