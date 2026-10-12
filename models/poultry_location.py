# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryLocation(models.Model):
    _name = 'poultry.location'
    _description = 'Poultry Location'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(
        string='Location Name',
        required=True,
        tracking=True,
        help='Name of the poultry location (e.g., House 1, Pen A)'
    )
    code = fields.Char(
        string='Code',
        tracking=True,
        help='Short code for the location'
    )
    location_type = fields.Selection([
        ('indoor', 'Indoor Pen'),
        ('outdoor', 'Outdoor Pen'),
    ], string='Location Type',
       required=True,
       default='indoor',
       tracking=True
    )
    capacity = fields.Integer(
        string='Bird Capacity',
        help='Maximum number of birds this location can hold',
        tracking=True
    )
    current_occupancy = fields.Integer(
        string='Current Occupancy',
        compute='_compute_current_occupancy',
        store=True,
        help='Current number of birds in this location'
    )
    current_dead_count = fields.Integer(
        string='Dead Birds',
        compute='_compute_current_occupancy',
        store=True,
        help='Number of birds that died (mortality) in this location'
    )
    current_slaughtered_count = fields.Integer(
        string='Slaughtered Birds',
        compute='_compute_current_occupancy',
        store=True,
        help='Number of birds that have been slaughtered/processed from this location'
    )
    current_culled_count = fields.Integer(
        string='Culled Birds',
        compute='_compute_current_occupancy',
        store=True,
        help='Number of birds currently culled (removed but not dead) in this location'
    )
    current_total_weight = fields.Float(
        string='Current Total Weight (g)',
        compute='_compute_current_occupancy',
        store=True,
        digits=(10, 2),
        help='Total weight of all birds currently in this location'
    )
    avg_weight = fields.Float(
        string='Average Weight (g)',
        compute='_compute_current_occupancy',
        store=True,
        digits=(10, 2),
        help='Average weight per bird in this location'
    )
    current_growth_tracking_id = fields.Many2one(
        'poultry.growth.tracking',
        string='Current Growth Tracking',
        compute='_compute_current_growth_tracking',
        help='Active growth tracking at this location'
    )
    growth_tracking_history_ids = fields.One2many(
        'poultry.growth.tracking',
        'poultry_location_id',
        string='Growth Tracking History',
        help='All growth tracking records at this location'
    )
    growth_history_count = fields.Integer(
        string='Growth History Count',
        compute='_compute_growth_history_count',
        help='Total number of growth tracking records at this location'
    )
    employee_ids = fields.One2many(
        'farm.employee',
        'poultry_location_id',
        string='Responsible Employees',
        help='Employees responsible for this location'
    )
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_employee_count',
        help='Number of employees assigned to this location'
    )
    processing_order_count = fields.Integer(
        string='Processing Orders',
        compute='_compute_processing_order_count',
        help='Number of manufacturing orders (processing) from this location'
    )
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        readonly=True,
        ondelete='restrict',
        help='Associated Odoo stock location'
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
        ('name_unique', 'unique(name)', 'Location name must be unique!'),
    ]
    
    @api.depends('growth_tracking_history_ids', 'growth_tracking_history_ids.state', 'growth_tracking_history_ids.current_quantity', 
                 'growth_tracking_history_ids.mortality_ids', 'growth_tracking_history_ids.mortality_ids.quantity',
                 'growth_tracking_history_ids.slaughter_ids', 'growth_tracking_history_ids.slaughter_ids.quantity_slaughtered',
                 'growth_tracking_history_ids.culling_ids', 'growth_tracking_history_ids.culling_ids.quantity',
                 'growth_tracking_history_ids.culling_ids.state')
    def _compute_current_occupancy(self):
        """Compute current occupancy based on growth tracking at this location"""
        for location in self:
            # Get active growth tracking directly from the One2many relationship
            active_growth = location.growth_tracking_history_ids.filtered(
                lambda g: g.state in ['partially_processed', 'confirmed']
            )
            if active_growth:
                # Take the first active one (should only be one)
                growth = active_growth[0]
                location.current_occupancy = growth.current_quantity
                
                # Calculate dead birds (mortality only)
                location.current_dead_count = sum(growth.mortality_ids.mapped('quantity'))
                
                # Calculate slaughtered birds
                location.current_slaughtered_count = sum(growth.slaughter_ids.mapped('quantity_slaughtered'))
                
                # Calculate culled birds (only those still in 'culled' state, not dead)
                location.current_culled_count = sum(
                    culling.quantity 
                    for culling in growth.culling_ids 
                    if culling.state == 'culled'
                )
                
                # Calculate total weight and average
                location.current_total_weight = (growth.current_weight * growth.current_quantity)/1000
                location.avg_weight = (location.current_total_weight / location.current_occupancy)/1000 if location.current_occupancy > 0 else 0.0
            else:
                location.current_occupancy = 0
                location.current_dead_count = 0
                location.current_slaughtered_count = 0
                location.current_culled_count = 0
                location.current_total_weight = 0.0
                location.avg_weight = 0.0
    
    @api.depends('growth_tracking_history_ids', 'growth_tracking_history_ids.state')
    def _compute_current_growth_tracking(self):
        """Find the current growth tracking at this location"""
        for location in self:
            # Get active growth tracking directly from the One2many relationship
            active_growth = location.growth_tracking_history_ids.filtered(
                lambda g: g.state in ['draft', 'confirmed']
            )
            location.current_growth_tracking_id = active_growth[0].id if active_growth else False
    
    def _compute_growth_history_count(self):
        """Count all growth tracking records at this location"""
        for location in self:
            location.growth_history_count = len(location.growth_tracking_history_ids)
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically create stock location"""
        records = super().create(vals_list)
        for record in records:
            if not record.stock_location_id:
                record._create_stock_location()
        return records
    
    def _create_stock_location(self):
        """Create corresponding stock location in Odoo"""
        self.ensure_one()
        
        # Get or create parent location
        parent_location = self.parent_location_id
        if not parent_location:
            # Look for or create a "Poultry Locations" parent
            parent_location = self.env['stock.location'].search([
                ('name', '=', 'Poultry Locations'),
                ('usage', '=', 'view')
            ], limit=1)
            
            if not parent_location:
                # Get the main warehouse location
                warehouse = self.env['stock.warehouse'].search([], limit=1)
                if not warehouse:
                    raise ValidationError(_('No warehouse found. Please create a warehouse first.'))
                
                parent_location = self.env['stock.location'].create({
                    'name': 'Poultry Locations',
                    'usage': 'view',
                    'location_id': warehouse.view_location_id.id,
                })
        
        # Create the stock location
        stock_location = self.env['stock.location'].create({
            'name': self.name,
            'location_id': parent_location.id,
            'usage': 'transit',
            'company_id': self.env.company.id,
        })
        
        self.stock_location_id = stock_location.id
    
    def write(self, vals):
        """Update stock location name if location name changes"""
        res = super().write(vals)
        if 'name' in vals:
            for record in self:
                if record.stock_location_id:
                    record.stock_location_id.name = vals['name']
        return res
    
    def unlink(self):
        """Prevent deletion if there are birds in the location"""
        for record in self:
            if record.current_occupancy > 0:
                raise ValidationError(
                    _('Cannot delete location "%s" as it currently has birds in it.') % record.name
                )
        return super().unlink()
    
    def action_view_current_flock(self):
        """Open the current growth tracking"""
        self.ensure_one()
        if not self.current_growth_tracking_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('No active growth tracking at this location.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Growth Tracking',
            'res_model': 'poultry.growth.tracking',
            'res_id': self.current_growth_tracking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_growth_history(self):
        """Open all growth tracking records for this location"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Growth History - {self.name}',
            'res_model': 'poultry.growth.tracking',
            'view_mode': 'list,form',
            'domain': [('poultry_location_id', '=', self.id)],
            'context': {'default_poultry_location_id': self.id},
            'target': 'current',
        }
    
    @api.depends('employee_ids')
    def _compute_employee_count(self):
        """Count employees assigned to this location"""
        for location in self:
            location.employee_count = len(location.employee_ids)
    
    def _compute_processing_order_count(self):
        """Count manufacturing orders from current growth tracking at this location"""
        for location in self:
            # Get current active growth tracking (partially processed or confirmed)
            active_growth = location.growth_tracking_history_ids.filtered(
                lambda g: g.state in ['partially_processed']
            )
            if active_growth:
                # Count MOs linked to current growth tracking
                mo_count = self.env['mrp.production'].search_count([
                    ('growth_tracking_id', '=', active_growth[0].id)
                ])
                location.processing_order_count = mo_count
            else:
                location.processing_order_count = 0
    
    def action_view_employees(self):
        """Open employees assigned to this location"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Employees - {self.name}',
            'res_model': 'farm.employee',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.employee_ids.ids)],
            'target': 'current',
        }
    
    def action_view_processing_orders(self):
        """Open manufacturing orders (processing) from current growth tracking"""
        self.ensure_one()
        # Get current active growth tracking
        active_growth = self.growth_tracking_history_ids.filtered(
            lambda g: g.state in ['partially_processed', 'confirmed']
        )
        if not active_growth:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No active growth tracking with processing orders.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Processing Orders - {self.name}',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('growth_tracking_id', '=', active_growth[0].id)],
            'context': {'create': False},
            'target': 'current',
        }
    
    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"[{record.code}] {name}"
            result.append((record.id, name))
        return result
