# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FarmEquipment(models.Model):
    _name = 'farm.equipment'
    _description = 'Farm Equipment & Assets'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    name = fields.Char(
        string='Equipment Name',
        required=True,
        tracking=True
    )
    equipment_type = fields.Selection([
        ('feeder', 'Feeder'),
        ('drinker', 'Drinker/Waterer'),
        ('heater', 'Heater'),
        ('fan', 'Ventilation Fan'),
        ('generator', 'Generator'),
        ('scale', 'Scale/Weighing Equipment'),
        ('incubator', 'Incubator'),
        ('catcher', 'Bird Catcher'),
        ('cage', 'Cage/Housing'),
        ('lighting', 'Lighting System'),
        ('other', 'Other')
    ], string='Equipment Type',
       required=True,
       tracking=True
    )
    location_id = fields.Many2one(
        'poultry.location',
        string='Location',
        tracking=True,
        help='Current location of the equipment'
    )
    serial_number = fields.Char(
        string='Serial Number',
        tracking=True
    )
    purchase_date = fields.Date(
        string='Purchase Date',
        tracking=True
    )
    purchase_cost = fields.Float(
        string='Purchase Cost',
        digits=(10, 2),
        tracking=True
    )
    status = fields.Selection([
        ('working', 'Working'),
        ('maintenance', 'Under Maintenance'),
        ('broken', 'Broken'),
        ('retired', 'Retired')
    ], string='Status',
       default='working',
       required=True,
       tracking=True
    )
    last_maintenance_date = fields.Date(
        string='Last Maintenance',
        tracking=True
    )
    next_maintenance_date = fields.Date(
        string='Next Maintenance Due',
        tracking=True
    )
    supplier_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        domain=[('supplier_rank', '>', 0)]
    )
    asset_id = fields.Many2one(
        'account.asset',
        string='Related Asset',
        readonly=True,
        tracking=True,
        help='Linked asset for depreciation tracking'
    )
    asset_count = fields.Integer(
        string='Asset Count',
        compute='_compute_asset_count'
    )
    notes = fields.Text(
        string='Notes'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    def _compute_asset_count(self):
        """Count linked assets"""
        for record in self:
            record.asset_count = 1 if record.asset_id else 0

    def action_create_asset(self):
        """Create an asset from this equipment"""
        self.ensure_one()
        
        if self.asset_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Asset'),
                'res_model': 'account.asset',
                'res_id': self.asset_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        if not self.purchase_cost or self.purchase_cost <= 0:
            raise UserError(_('Please set a purchase cost before creating an asset.'))
        
        # Create asset directly - Odoo 18 doesn't use asset categories
        asset_vals = {
            'name': self.name,
            'original_value': self.purchase_cost,
            'acquisition_date': self.purchase_date or fields.Date.today(),
            'state': 'draft',
        }
        
        asset = self.env['account.asset'].create(asset_vals)
        
        # Link asset to equipment
        self.asset_id = asset.id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset'),
            'res_model': 'account.asset',
            'res_id': asset.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_asset(self):
        """Open the related asset"""
        self.ensure_one()
        
        if not self.asset_id:
            return self.action_create_asset()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset'),
            'res_model': 'account.asset',
            'res_id': self.asset_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
