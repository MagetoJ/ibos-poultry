# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PoultryWaterConsumption(models.Model):
    _name = 'poultry.water.consumption'
    _description = 'Poultry Water Consumption'
    _order = 'date desc, id desc'

    flock_id = fields.Many2one(
        'poultry.flock',
        string='Flock',
        ondelete='cascade',
        index=True
    )
    growth_tracking_id = fields.Many2one(
        'poultry.growth.tracking',
        string='Growth Tracking',
        ondelete='cascade',
        index=True,
        help='Link to growth tracking record if applicable'
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    quantity = fields.Float(
        string='Quantity (Liters)',
        required=True,
        digits=(10, 2),
        help='Water consumed in liters'
    )
    notes = fields.Text(
        string='Notes'
    )

    @api.constrains('flock_id', 'growth_tracking_id')
    def _check_flock_or_growth_tracking(self):
        """Ensure either flock_id or growth_tracking_id is set"""
        for record in self:
            if not record.flock_id and not record.growth_tracking_id:
                raise ValidationError(_('Either Flock or Growth Tracking must be set.'))

    @api.constrains('quantity')
    def _check_quantity(self):
        """Validate quantity"""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))
