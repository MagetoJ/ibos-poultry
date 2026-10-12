# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class CleaningSchedule(models.Model):
    _name = 'cleaning.schedule'
    _description = 'Cleaning Schedule Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'location_id, frequency'
    
    name = fields.Char(
        string='Task Name',
        required=True,
        help='Name of the cleaning task'
    )
    location_id = fields.Many2one(
        'poultry.location',
        string='Location',
        help='Specific location (leave empty for general tasks)'
    )
    area_type = fields.Selection([
        ('brooding', 'Brooding Area'),
        ('growing', 'Growing Shed'),
        ('processing', 'Processing Area'),
        ('feed_storage', 'Feed Storage'),
        ('equipment', 'Equipment'),
        ('general', 'General Area'),
        ('other', 'Other')
    ], string='Area Type',
       required=True
    )
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('monthly', 'Monthly'),
        ('per_batch', 'Per Batch (Before New Flock)'),
        ('as_needed', 'As Needed')
    ], string='Frequency',
       required=True,
       default='weekly'
    )
    day_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ], string='Day of Week',
       help='Specific day for weekly/bi-weekly schedules'
    )
    responsible_id = fields.Many2one(
        'farm.employee',
        string='Responsible Person',
        help='Employee responsible for this task'
    )
    cleaning_type = fields.Selection([
        ('sweep', 'Sweeping'),
        ('wash', 'Washing'),
        ('disinfect', 'Disinfection'),
        ('fumigate', 'Fumigation'),
        ('pest_control', 'Pest Control'),
        ('waste_removal', 'Waste Removal'),
        ('equipment_maintenance', 'Equipment Maintenance'),
        ('other', 'Other')
    ], string='Cleaning Type',
       required=True
    )
    products_required = fields.Text(
        string='Products/Supplies Required',
        help='List of cleaning products or supplies needed'
    )
    instructions = fields.Text(
        string='Instructions',
        help='Detailed cleaning instructions'
    )
    estimated_duration = fields.Float(
        string='Estimated Duration (hours)',
        digits=(5, 2),
        help='Estimated time to complete the task'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
