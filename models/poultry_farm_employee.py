# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class FarmEmployee(models.Model):
    _name = 'farm.employee'
    _description = 'Farm Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True
    )
    employee_id = fields.Char(
        string='Employee ID',
        tracking=True
    )
    role = fields.Selection([
        ('manager', 'Farm Manager'),
        ('supervisor', 'Supervisor'),
        ('technician', 'Poultry Technician'),
        ('veterinarian', 'Veterinarian'),
        ('worker', 'General Worker'),
        ('cleaner', 'Cleaner'),
        ('feeder', 'Feeder'),
        ('other', 'Other')
    ], string='Role',
       required=True,
       tracking=True
    )
    phone = fields.Char(
        string='Phone',
        tracking=True
    )
    email = fields.Char(
        string='Email',
        tracking=True
    )
    date_hired = fields.Date(
        string='Date Hired',
        tracking=True
    )
    hr_employee_id = fields.Many2one(
        'hr.employee',
        string='Related  Employee',
        tracking=True,
        readonly=True,
        help='Link to employee record in HR module'
    )
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_employee_count'
    )
    poultry_location_id = fields.Many2one(
        'poultry.location',
        string='Assigned Location',
        tracking=True,
        help='Poultry location this employee is responsible for'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    notes = fields.Text(
        string='Notes'
    )
    
    _sql_constraints = [
        ('employee_id_unique', 'UNIQUE(employee_id)', 
         'Employee ID must be unique!'),
    ]

    @api.depends('hr_employee_id')
    def _compute_employee_count(self):
        """Count linked HR employees"""
        for record in self:
            record.employee_count = 1 if record.hr_employee_id else 0

    @api.onchange('hr_employee_id')
    def _onchange_hr_employee(self):
        """Auto-fill information from HR employee"""
        if self.hr_employee_id:
            if not self.name:
                self.name = self.hr_employee_id.name
            if not self.phone:
                self.phone = self.hr_employee_id.work_phone or self.hr_employee_id.mobile_phone
            if not self.email:
                self.email = self.hr_employee_id.work_email

    def action_create_employee(self):
        """Create an HR employee from this farm employee"""
        self.ensure_one()
        
        if self.hr_employee_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Employee'),
                'res_model': 'hr.employee',
                'res_id': self.hr_employee_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        # Create HR employee
        employee_vals = {
            'name': self.name,
            'work_phone': self.phone,
            'work_email': self.email,
        }
        
        employee = self.env['hr.employee'].create(employee_vals)
        
        # Link to farm employee
        self.hr_employee_id = employee.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee'),
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_employee(self):
        """Open the related HR employee"""
        self.ensure_one()
        
        if not self.hr_employee_id:
            return self.action_create_employee()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee'),
            'res_model': 'hr.employee',
            'res_id': self.hr_employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_location(self):
        """Open the assigned location"""
        self.ensure_one()
        
        if not self.poultry_location_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No location assigned to this employee.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Location - {self.name}',
            'res_model': 'poultry.location',
            'res_id': self.poultry_location_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
