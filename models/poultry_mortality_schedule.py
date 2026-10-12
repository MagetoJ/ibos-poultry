# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MortalitySchedule(models.Model):
    _name = 'mortality.schedule'
    _description = 'Mortality Schedule Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    name = fields.Char(
        string='Schedule Name',
        required=True,
        help='Name of the mortality schedule (e.g., HW Mortality Schedule, PR Mortality Schedule)'
    )
    bird_type = fields.Selection([
        ('broiler', 'Broiler'),
        ('layer', 'Layer'),
        ('breeder', 'Breeder'),
        ('other', 'Other')
    ], string='Bird Type',
       required=True,
       default='broiler'
    )
    line_ids = fields.One2many(
        'mortality.schedule.line',
        'schedule_id',
        string='Schedule Lines',
        help='Daily mortality rate by age'
    )
    notes = fields.Text(
        string='Notes',
        help='General notes about this mortality schedule'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )


class MortalityScheduleLine(models.Model):
    _name = 'mortality.schedule.line'
    _description = 'Mortality Schedule Line'
    _order = 'schedule_id, age_from'
    
    schedule_id = fields.Many2one(
        'mortality.schedule',
        string='Mortality Schedule',
        required=True,
        ondelete='cascade'
    )
    age_from = fields.Integer(
        string='Age From (Days)',
        required=True,
        help='Starting age in days'
    )
    age_to = fields.Integer(
        string='Age To (Days)',
        required=True,
        help='Ending age in days'
    )
    mortality_rate = fields.Float(
        string='Mortality Rate (%)',
        digits=(10, 4),
        required=True,
        help='Expected daily mortality rate as percentage of current population'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes for this age range'
    )
    
    _sql_constraints = [
        ('age_check', 'CHECK(age_to >= age_from)', 
         'Age To must be greater than or equal to Age From!'),
        ('mortality_rate_check', 'CHECK(mortality_rate >= 0 AND mortality_rate <= 100)', 
         'Mortality rate must be between 0 and 100!'),
    ]
