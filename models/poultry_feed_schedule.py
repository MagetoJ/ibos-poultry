# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class FeedSchedule(models.Model):
    _name = 'feed.schedule'
    _description = 'Feed Schedule Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    name = fields.Char(
        string='Schedule Name',
        required=True,
        help='Name of the feeding schedule (e.g., HW Schedule, PR Schedule)'
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
        'feed.schedule.line',
        'schedule_id',
        string='Schedule Lines',
        help='Daily feeding schedule by age'
    )
    notes = fields.Text(
        string='Notes',
        help='General notes about this feeding schedule'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )


class FeedScheduleLine(models.Model):
    _name = 'feed.schedule.line'
    _description = 'Feed Schedule Line'
    _order = 'schedule_id, age_from'
    
    schedule_id = fields.Many2one(
        'feed.schedule',
        string='Feed Schedule',
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
    feed_product_id = fields.Many2one(
        'product.product',
        string='Feed Product',
        domain=[('poultry_product_type', '=', 'feed')],
        required=True,
        help='Feed product for this age range'
    )
    quantity_per_bird = fields.Float(
        string='Quantity per Bird (kg/day)',
        digits=(10, 3),
        required=True,
        help='Daily feed per bird in kg'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional instructions for this age range'
    )
    
    _sql_constraints = [
        ('age_check', 'CHECK(age_to >= age_from)', 
         'Age To must be greater than or equal to Age From!'),
    ]
