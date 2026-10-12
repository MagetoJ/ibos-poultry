# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryWeighing(models.Model):
    _name = 'poultry.weighing'
    _description = 'Poultry Weighing Record'
    _rec_name = 'weighing_date'
    _order = 'weighing_date desc, id desc'
    
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
    poultry_location_id = fields.Many2one(
        'poultry.location',
        string='Location',
        ondelete='set null',
        compute='_compute_location_id',
        store=True,
        index=True,
        help='Location where the weighing was performed'
    )
    weighing_date = fields.Date(
        string='Weighing Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    sample_size = fields.Integer(
        string='Sample Size',
        required=True,
        default=10,
        help='Number of birds weighed for average calculation'
    )
    age_from = fields.Integer(
        string='Age (Days)',
        help='Starting age in days for this weighing record'
    )
    age_to = fields.Integer(
        string='Age To (Days)',
        help='Ending age in days for this weighing record'
    )
    average_weight = fields.Float(
        string='Average Weight (g)',
        required=True,
        digits=(10, 2),
        help='Average weight per bird in kilograms'
    )
    total_sample_weight = fields.Float(
        string='Total Sample Weight (g)',
        compute='_compute_total_sample_weight',
        store=True,
        digits=(10, 2),
        help='Total weight of sample (sample_size × average_weight)'
    )
    notes = fields.Text(
        string='Notes'
    )
    
    _sql_constraints = [
        ('sample_size_positive', 'CHECK(sample_size > 0)', 
         'Sample size must be greater than zero!'),
        ('average_weight_positive_v2', 'CHECK(average_weight >= 0)', 
         'Average weight must be greater than or equal to zero!'),
    ]

    @api.depends('flock_id','flock_id.location_id',)
    def _compute_location_id(self):
        """Compute location_id based on flock or growth tracking"""
        for record in self:
            if record.flock_id:
                record.poultry_location_id = record.flock_id.poultry_location_id
            else:
                record.poultry_location_id = False
    
    @api.constrains('flock_id', 'growth_tracking_id')
    def _check_flock_or_growth_tracking(self):
        """Ensure either flock_id or growth_tracking_id is set"""
        for record in self:
            if not record.flock_id and not record.growth_tracking_id:
                raise ValidationError(_('Either Flock or Growth Tracking must be set.'))
    
    @api.depends('sample_size', 'average_weight')
    def _compute_total_sample_weight(self):
        """Calculate total sample weight"""
        for record in self:
            record.total_sample_weight = record.sample_size * record.average_weight

    def name_get(self):
        """Override name_get for better display"""
        result = []
        for record in self:
            if record.growth_tracking_id:
                name = f"Weighing - {record.growth_tracking_id.flock_id.flock_code} ({record.weighing_date})"
            elif record.flock_id:
                name = f"Weighing - {record.flock_id.flock_code} ({record.weighing_date})"
            else:
                name = f"Weighing - {record.weighing_date}"
            result.append((record.id, name))
        return result
