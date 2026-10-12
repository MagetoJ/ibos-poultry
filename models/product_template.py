# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    poultry_product_type = fields.Selection([
        ('chick', 'Day-Old Chick'),
        ('feed', 'Poultry Feed'),
        ('medicine', 'Poultry Medicine/Vaccine'),
        ('gas', 'Gas'),
        ('other', 'Poultry Associated Cost'),
        ('etc', 'Other Non Cost Product')
    ], string='Poultry Product Type', 
       help='Classify this product for poultry management operations'
    )

    is_farm_raw_material = fields.Boolean(
        string='Farm Raw Material',
        help='Check if this product is a farm raw material for on hand tracking.'
    )
