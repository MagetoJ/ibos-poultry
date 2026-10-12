# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryWeightSchedule(models.Model):
    _name = 'weight.schedule'
    _description = 'Poultry Weight Schedule'
    _rec_name = 'name'
    _order = 'name'
    
    name = fields.Char(
        string='Schedule Name',
        required=True,
        help='Name of the weight schedule'
    )
    bird_type = fields.Selection([
        ('broiler', 'Broiler'),
        ('layer', 'Layer'),
    ], string='Bird Type',
       required=True,
       default='broiler',
       help='Type of bird this schedule is for'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    line_ids = fields.One2many(
        'weight.schedule.line',
        'schedule_id',
        string='Schedule Lines',
        help='Daily weight schedule entries'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional information about this weight schedule'
    )
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Schedule name must be unique!'),
    ]


class PoultryWeightScheduleLine(models.Model):
    _name = 'weight.schedule.line'
    _description = 'Poultry Weight Schedule Line'
    _rec_name = 'age_from'
    _order = 'schedule_id, age_from'
    
    schedule_id = fields.Many2one(
        'weight.schedule',
        string='Weight Schedule',
        required=True,
        ondelete='cascade',
        index=True
    )
    age_from = fields.Integer(
        string='Age (Days)',
        required=True,
        help='Age in days'
    )
    age_to = fields.Integer(
        string='Age To (Days)',
        required=True,
        help='End age in days (typically same as age_from for daily schedules)'
    )
    expected_weight = fields.Float(
        string='Expected Weight (g)',
        required=True,
        digits=(10, 2),
        help='Expected average weight per bird in grams'
    )
    
    _sql_constraints = [
        ('age_from_positive', 'CHECK(age_from >= 0)', 
         'Age must be zero or positive!'),
        ('age_to_positive', 'CHECK(age_to >= 0)', 
         'Age To must be zero or positive!'),
        ('age_to_gte_age_from', 'CHECK(age_to >= age_from)', 
         'Age To must be greater than or equal to Age From!'),
        ('expected_weight_positive', 'CHECK(expected_weight >= 0)', 
         'Expected weight must be zero or positive!'),
    ]
    
    @api.constrains('age_from', 'age_to', 'schedule_id')
    def _check_age_overlap(self):
        """Check for overlapping age ranges in the same schedule"""
        for record in self:
            overlapping = self.search([
                ('schedule_id', '=', record.schedule_id.id),
                ('id', '!=', record.id),
                ('age_from', '<=', record.age_to),
                ('age_to', '>=', record.age_from)
            ])
            if overlapping:
                raise ValidationError(_(
                    'Age range %d-%d overlaps with existing schedule line(s).'
                ) % (record.age_from, record.age_to))
