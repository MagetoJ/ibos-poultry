# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultrySlaughter(models.Model):
    _name = 'poultry.slaughter'
    _description = 'Poultry Slaughter Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'slaughter_date desc, id desc'
    
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    growth_tracking_id = fields.Many2one(
        'poultry.growth.tracking',
        string='Growth Tracking',
        required=True,
        ondelete='cascade',
        tracking=True,
        help='Growth tracking record being slaughtered'
    )
    flock_id = fields.Many2one(
        'poultry.flock',
        string='Flock',
        related='growth_tracking_id.flock_id',
        store=True,
        readonly=True
    )
    batch_number = fields.Char(
        string='Batch Number',
        related='flock_id.name',
        readonly=True
    )
    poultry_location_id = fields.Many2one(
        'poultry.location',
        string='Location',
        related='growth_tracking_id.poultry_location_id',
        store=True,
        readonly=True
    )
    slaughter_date = fields.Date(
        string='Slaughter Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date when birds were slaughtered'
    )
    quantity_to_slaughter = fields.Integer(
        string='Quantity to Slaughter',
        required=True,
        tracking=True,
        help='Number of birds to be slaughtered'
    )
    quantity_slaughtered = fields.Integer(
        string='Quantity Slaughtered',
        compute='_compute_quantity_slaughtered',
        store=True,
        help='Actual number of birds slaughtered'
    )
    available_birds = fields.Integer(
        string='Available Birds',
        related='growth_tracking_id.current_quantity',
        help='Number of birds available for slaughter'
    )
    average_weight = fields.Float(
        string='Average Live Weight (g)',
        digits=(10, 2),
        tracking=True,
        help='Average weight per bird at slaughter'
    )
    total_live_weight = fields.Float(
        string='Total Live Weight (g)',
        compute='_compute_total_weights',
        store=True,
        digits=(10, 2),
        help='Total live weight of birds slaughtered'
    )
    total_live_weight_kg = fields.Float(
        string='Total Live Weight (kg)',
        compute='_compute_total_weights',
        store=True,
        digits=(10, 3),
        help='Total live weight in kilograms'
    )
    age_at_slaughter = fields.Integer(
        string='Age at Slaughter (Days)',
        related='growth_tracking_id.age_days',
        readonly=True,
        help='Age of birds at slaughter'
    )
    slaughter_house = fields.Char(
        string='Slaughter House',
        tracking=True,
        help='Name of the slaughter facility'
    )
    buyer = fields.Many2one(
        'res.partner',
        string='Buyer',
        tracking=True,
        help='Customer purchasing the slaughtered birds'
    )
    price_per_kg = fields.Float(
        string='Price per Kg',
        digits=(10, 2),
        tracking=True,
        help='Selling price per kilogram'
    )
    total_revenue = fields.Float(
        string='Total Revenue',
        compute='_compute_revenue',
        store=True,
        digits=(10, 2),
        help='Total revenue from sale'
    )
    transport_cost = fields.Float(
        string='Transport Cost',
        digits=(10, 2),
        tracking=True,
        help='Cost of transporting birds to slaughter'
    )
    slaughter_cost = fields.Float(
        string='Slaughter/Processing Cost',
        digits=(10, 2),
        tracking=True,
        help='Cost of slaughter and processing'
    )
    other_costs = fields.Float(
        string='Other Costs',
        digits=(10, 2),
        tracking=True,
        help='Other miscellaneous costs'
    )
    total_costs = fields.Float(
        string='Total Costs',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Total costs associated with slaughter'
    )
    net_profit = fields.Float(
        string='Net Profit',
        compute='_compute_net_profit',
        store=True,
        digits=(10, 2),
        help='Net profit from slaughter (Revenue - Costs)'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status',
       default='draft',
       required=True,
       tracking=True
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the slaughter'
    )
    
    # Smart button counts
    manufacturing_order_count = fields.Integer(
        string='Manufacturing Orders',
        compute='_compute_manufacturing_order_count',
        help='Count of related manufacturing orders'
    )
    
    _sql_constraints = [
        ('quantity_positive', 'CHECK(quantity_to_slaughter > 0)', 
         'Quantity to slaughter must be greater than zero!'),
    ]
    
    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence for reference"""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('poultry.slaughter') or _('New')
        return super().create(vals_list)
    
    @api.depends('quantity_to_slaughter', 'state')
    def _compute_quantity_slaughtered(self):
        """Compute actual quantity slaughtered based on state"""
        for record in self:
            if record.state == 'completed':
                record.quantity_slaughtered = record.quantity_to_slaughter
            else:
                record.quantity_slaughtered = 0
    
    @api.depends('quantity_to_slaughter', 'average_weight')
    def _compute_total_weights(self):
        """Calculate total live weight"""
        for record in self:
            record.total_live_weight = record.quantity_to_slaughter * record.average_weight
            record.total_live_weight_kg = record.total_live_weight / 1000.0
    
    @api.depends('total_live_weight_kg', 'price_per_kg')
    def _compute_revenue(self):
        """Calculate total revenue based on live weight"""
        for record in self:
            record.total_revenue = record.total_live_weight_kg * record.price_per_kg
    
    @api.depends('transport_cost', 'slaughter_cost', 'other_costs')
    def _compute_total_costs(self):
        """Calculate total costs"""
        for record in self:
            record.total_costs = record.transport_cost + record.slaughter_cost + record.other_costs
    
    @api.depends('total_revenue', 'total_costs')
    def _compute_net_profit(self):
        """Calculate net profit"""
        for record in self:
            record.net_profit = record.total_revenue - record.total_costs
    
    def _compute_manufacturing_order_count(self):
        """Compute count of related manufacturing orders"""
        for record in self:
            # Find MOs that reference this slaughter record
            mo_count = self.env['mrp.production'].search_count([
                ('slaughter_id', '=', record.id)
            ])
            record.manufacturing_order_count = mo_count
    
    @api.constrains('quantity_to_slaughter', 'growth_tracking_id')
    def _check_quantity(self):
        """Validate quantity against available birds"""
        for record in self:
            if record.quantity_to_slaughter > record.growth_tracking_id.current_quantity:
                raise ValidationError(_(
                    'Cannot slaughter %d birds. Only %d birds available in growth tracking.'
                ) % (record.quantity_to_slaughter, record.growth_tracking_id.current_quantity))
    
    def action_schedule(self):
        """Schedule the slaughter"""
        self.ensure_one()
        self.state = 'scheduled'
    
    def action_complete(self):
        """Mark slaughter as completed and update growth tracking"""
        self.ensure_one()
        self.state = 'completed'
        # Update growth tracking state to slaughtered only if all birds are processed
        if self.growth_tracking_id:
            total_slaughtered = sum(self.growth_tracking_id.slaughter_ids.mapped('quantity_slaughtered'))
            if total_slaughtered >= self.growth_tracking_id.initial_quantity:
                self.growth_tracking_id.state = 'slaughtered'
                # Also close the flock
                if self.growth_tracking_id.flock_id:
                    self.growth_tracking_id.flock_id.state = 'closed'
    
    def action_cancel(self):
        """Cancel the slaughter"""
        self.ensure_one()
        self.state = 'cancelled'
    
    def action_draft(self):
        """Set back to draft"""
        self.ensure_one()
        self.state = 'draft'
    
    def action_view_manufacturing_order(self):
        """Open the related manufacturing order"""
        self.ensure_one()
        
        # Find the MO that references this slaughter record
        mo = self.env['mrp.production'].search([
            ('slaughter_id', '=', self.id)
        ], limit=1)
        
        if not mo:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Manufacturing Order',
            'res_model': 'mrp.production',
            'res_id': mo.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name} - {record.batch_number} ({record.slaughter_date})"
            result.append((record.id, name))
        return result
