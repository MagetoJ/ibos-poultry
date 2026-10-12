# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryFlock(models.Model):
    _name = 'poultry.flock'
    _description = 'Poultry Flock/Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_received desc, name desc'
    
    name = fields.Char(string='Batch Number',required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        readonly=True,
        tracking=True,
        help='Purchase order from which chicks were received'
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Receipt',
        readonly=True,
        help='Stock receipt for this flock'
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        readonly=True,
        help='Lot/serial number for tracking this flock in inventory'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Chick Product',
        required=True,
        domain=[('poultry_product_type', '=', 'chick')],
        readonly=True,
        tracking=True
    )
    date_received = fields.Datetime(
        string='Date Received',
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        tracking=True,
        help='Date when chicks were received'
    )
    initial_quantity = fields.Integer(
        string='Initial Quantity',
        required=True,
        readonly=True,
        tracking=True,
        help='Number of chicks received'
    )
    current_quantity = fields.Integer(
        string='Current Quantity',
        compute='_compute_current_quantity',
        store=True,
        help='Current number of birds alive'
    )
    mortality_count = fields.Integer(
        string='Total Mortality',
        compute='_compute_mortality',
        store=True,
        help='Total number of birds that died'
    )
    mortality_rate = fields.Float(
        string='Mortality Rate (%)',
        compute='_compute_mortality',
        store=True,
        digits=(5, 2)
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        required=True,
        domain=[('usage', '=', 'internal')],
        tracking=True,
        readonly=True,
        help='Current location where flock is housed'
    )
    poultry_location_id = fields.Many2one(
        'poultry.location',
        string='Poultry Location',
        tracking=True,
        readonly=True,
        help='Poultry management location'
    )
    state = fields.Selection([
        ('received', 'Received'),
        ('growing', 'Brooding'),
        ('transfer', 'Grow Out'),
        ('closed', 'Closed')
    ], string='Status',
       default='received',
       required=True,
       tracking=True
    )
    lights_on_date = fields.Date(
        string='Lights On Date',
        compute='_compute_lights_on_date',
        store=True,
        help='Date when lights/electricity started in staging (same as receipt date)'
    )
    estimated_lights_off_date = fields.Date(
        string='Estimated Lights Off Date',
        help='Estimated date when lights/electricity will be turned off (default: 10 days after receipt)'
    )
    staging_days_with_lights = fields.Integer(
        string='Days with Lights',
        compute='_compute_staging_days',
        help='Number of days with lights/electricity in staging'
    )
    staging_days_without_lights = fields.Integer(
        string='Days without Lights',
        compute='_compute_staging_days',
        help='Number of days without lights/electricity in staging'
    )
    total_staging_days = fields.Integer(
        string='Total Brooder Days',
        compute='_compute_staging_days',
        help='Total days in staging area'
    )
    initial_weight = fields.Float(
        string='Initial Average Weight (g)',
        digits=(10, 2),
        tracking=True,
        required=True,
        help='Average weight per bird at receipt (in kilograms)'
    )
    sample_size = fields.Integer(
        string='Default Sample Size',
        default=10,
        required=True,
        help='Number of birds weighed for average calculation'
    )
    current_weight = fields.Float(
        string='Current Average Weight (g)',
        compute='_compute_current_weight',
        store=True,
        digits=(10, 2),
        help='Current average weight per bird from latest weighing record'
    )
    target_weight = fields.Float(
        string='Target Weight (g)',
        digits=(10, 2),
        tracking=True,
        required=True,
        help='Target average weight per bird'
    )
    weight_progress = fields.Float(
        string='Weight Progress (%)',
        compute='_compute_weight_progress',
        store=True,
        help='Progress towards target weight'
    )
    initial_cost_per_bird = fields.Float(
        string='Initial Cost/Bird',
        readonly=True,
        help='Purchase cost per bird'
    )
    current_cost_per_bird = fields.Float(
        string='Current Cost/Bird',
        compute='_compute_current_cost',
        store=True,
        help='Current accumulated cost per bird (including feed, medicine, etc.)'
    )
    total_feed_cost = fields.Float(
        string='Total Feed Cost',
        compute='_compute_total_costs',
        store=True,
        help='Total cost of feed consumed by this flock'
    )
    total_medicine_cost = fields.Float(
        string='Total Medicine Cost',
        compute='_compute_total_costs',
        store=True,
        help='Total cost of medicine used for this flock'
    )
    total_gas_cost = fields.Float(
        string='Total Gas Cost',
        compute='_compute_total_costs',
        store=True,
        help='Total cost of gas consumed by this flock'
    )
    total_cost = fields.Float(
        string='Total Cost',
        compute='_compute_total_costs',
        store=True,
        help='Total accumulated cost for this flock'
    )
    age_days = fields.Integer(
        string='Age (Days)',
        compute='_compute_age',
        help='Age of flock in days'
    )
    feed_consumption_ids = fields.One2many(
        'poultry.feed.consumption',
        'flock_id',
        string='Feed Consumption',
        help='Feed consumption records for this flock'
    )
    gas_consumption_ids = fields.One2many(
        'poultry.gas.consumption',
        'flock_id',
        string='Gas Consumption',
        help='Gas consumption records for this flock'
    )
    medicine_usage_ids = fields.One2many(
        'poultry.medicine.usage',
        'flock_id',
        string='Medicine/Vaccine Usage',
        help='Medicine and vaccine usage records for this flock'
    )
    mortality_ids = fields.One2many(
        'poultry.mortality',
        'flock_id',
        string='Mortality Records',
        help='Mortality records for this flock'
    )
    culling_ids = fields.One2many(
        'poultry.culling',
        'flock_id',
        string='Culling Records',
        help='Culling records for this flock'
    )
    weighing_ids = fields.One2many(
        'poultry.weighing',
        'flock_id',
        string='Weighing Records',
        help='Weight measurement records for this flock'
    )
    notes = fields.Text(
        string='Notes'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    purchase_order_count = fields.Integer(
        string='Purchase Order Count',
        compute='_compute_purchase_order_count'
    )
    picking_count = fields.Integer(
        string='Picking Count',
        compute='_compute_picking_count'
    )
    mortality_records_count = fields.Integer(
        string='Mortality Records Count',
        compute='_compute_mortality_records_count'
    )
    transfer_count = fields.Integer(
        string='Transfer Count',
        compute='_compute_transfer_count'
    )
    growth_tracking_count = fields.Integer(
        string='Growth Tracking Count',
        compute='_compute_growth_tracking_count'
    )
    feed_consumption_count = fields.Integer(
        string='Feed Records',
        compute='_compute_record_counts'
    )
    medicine_usage_count = fields.Integer(
        string='Medicine Records',
        compute='_compute_record_counts'
    )
    weighing_count = fields.Integer(
        string='Weighing Records',
        compute='_compute_record_counts'
    )



    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence for batch number"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('poultry.flock') or 'New'
        return super().create(vals_list)

    @api.depends('date_received')
    def _compute_age(self):
        """Calculate age in days"""
        for flock in self:
            if flock.date_received:
                delta = fields.Datetime.now() - flock.date_received
                flock.age_days = delta.days
            else:
                flock.age_days = 0
    
    @api.depends('date_received')
    def _compute_lights_on_date(self):
        """Set lights on date to receipt date"""
        for flock in self:
            flock.lights_on_date = flock.date_received.date() if flock.date_received else False
    
    @api.onchange('date_received')
    def _onchange_date_received(self):
        """Set estimated lights off date to 10 days after receipt"""
        if self.date_received and not self.estimated_lights_off_date:
            from datetime import timedelta
            self.estimated_lights_off_date = self.date_received.date() + timedelta(days=10)
    
    @api.depends('lights_on_date', 'estimated_lights_off_date', 'date_received')
    def _compute_staging_days(self):
        """Calculate staging days with and without lights"""
        for flock in self:
            today = fields.Date.today()
            received_date = flock.date_received.date() if flock.date_received else today
            
            # Days with lights
            if flock.lights_on_date and flock.estimated_lights_off_date:
                delta = flock.estimated_lights_off_date - flock.lights_on_date
                flock.staging_days_with_lights = max(0, delta.days)
            elif flock.lights_on_date:
                # Still running with lights
                delta = today - flock.lights_on_date
                flock.staging_days_with_lights = max(0, delta.days)
            else:
                flock.staging_days_with_lights = 0
            
            # Days without lights (after lights off)
            if flock.estimated_lights_off_date:
                if flock.state == 'transfer':
                    # Already transferred, calculate up to transfer date (use today as proxy)
                    delta = today - flock.estimated_lights_off_date
                else:
                    # Still in staging
                    delta = today - flock.estimated_lights_off_date
                flock.staging_days_without_lights = max(0, delta.days)
            else:
                flock.staging_days_without_lights = 0
                flock.staging_days_without_lights = 0
            
            # Total staging days
            flock.total_staging_days = flock.staging_days_with_lights + flock.staging_days_without_lights

    @api.depends('weighing_ids.weighing_date', 'weighing_ids.average_weight')
    def _compute_current_weight(self):
        """Get current weight from latest weighing record"""
        for flock in self:
            latest_weighing = flock.weighing_ids.sorted('weighing_date', reverse=True)[:1]
            flock.current_weight = latest_weighing.average_weight if latest_weighing else flock.initial_weight

    @api.depends('initial_weight', 'current_weight', 'target_weight')
    def _compute_weight_progress(self):
        """Calculate weight progress percentage"""
        for flock in self:
            if flock.target_weight and flock.target_weight > flock.initial_weight:
                weight_gained = flock.current_weight - flock.initial_weight
                target_gain = flock.target_weight - flock.initial_weight
                flock.weight_progress = (weight_gained / target_gain) * 100 if target_gain > 0 else 0.0
            else:
                flock.weight_progress = 0.0

    @api.depends('initial_quantity', 'mortality_ids.quantity', 'culling_ids.quantity', 'culling_ids.state')
    def _compute_current_quantity(self):
        """Calculate current quantity based on mortality and culling records"""
        for flock in self:
            # Deaths from mortality records
            dead_count = sum(flock.mortality_ids.mapped('quantity'))
            
            # Culled birds that are still culled (not recovered, not dead)
            culled_count = sum(
                culling.quantity 
                for culling in flock.culling_ids 
                if culling.state == 'culled'
            )
            
            # Culled birds that died
            culled_dead_count = sum(
                culling.quantity 
                for culling in flock.culling_ids 
                if culling.state == 'dead'
            )
            
            # Current quantity = initial - deaths - still culled - culled dead
            flock.current_quantity = flock.initial_quantity - dead_count - culled_count - culled_dead_count

    @api.depends('initial_quantity', 'current_quantity', 'mortality_ids.quantity', 'culling_ids.quantity', 'culling_ids.state')
    def _compute_mortality(self):
        """Calculate mortality statistics"""
        for flock in self:
            # Total dead = mortality records + culled dead
            dead_from_mortality = sum(flock.mortality_ids.mapped('quantity'))
            dead_from_culling = sum(
                culling.quantity 
                for culling in flock.culling_ids 
                if culling.state == 'dead'
            )
            flock.mortality_count = dead_from_mortality + dead_from_culling
            
            if flock.initial_quantity > 0:
                flock.mortality_rate = (flock.mortality_count / flock.initial_quantity) * 100
            else:
                flock.mortality_rate = 0.0

    @api.depends('initial_cost_per_bird', 'initial_quantity', 'feed_consumption_ids.total_cost', 'medicine_usage_ids.total_cost', 'gas_consumption_ids.total_cost')
    def _compute_total_costs(self):
        """Calculate total costs"""
        for flock in self:
            flock.total_feed_cost = sum(flock.feed_consumption_ids.mapped('total_cost'))
            flock.total_medicine_cost = sum(flock.medicine_usage_ids.mapped('total_cost'))
            flock.total_gas_cost = sum(flock.gas_consumption_ids.mapped('total_cost'))
            initial_cost = flock.initial_cost_per_bird * flock.initial_quantity
            flock.total_cost = initial_cost + flock.total_feed_cost + flock.total_medicine_cost + flock.total_gas_cost

    @api.depends('total_cost', 'initial_quantity')
    def _compute_current_cost(self):
        """Calculate current cost per bird based on initial quantity"""
        for flock in self:
            if flock.initial_quantity > 0:
                flock.current_cost_per_bird = flock.total_cost / flock.initial_quantity
            else:
                flock.current_cost_per_bird = 0.0

    def _compute_purchase_order_count(self):
        """Count related purchase orders"""
        for flock in self:
            flock.purchase_order_count = 1 if flock.purchase_order_id else 0

    def _compute_picking_count(self):
        """Count related pickings"""
        for flock in self:
            flock.picking_count = 1 if flock.picking_id else 0

    def _compute_mortality_records_count(self):
        """Count mortality records"""
        for flock in self:
            flock.mortality_records_count = len(flock.mortality_ids)

    def _compute_transfer_count(self):
        """Count related internal transfers"""
        for flock in self:
            # Count stock pickings with internal type that originated from this flock
            transfers = self.env['stock.picking'].search([
                ('origin', '=', flock.name),
                ('picking_type_id.code', '=', 'internal')
            ])
            flock.transfer_count = len(transfers)

    def _compute_growth_tracking_count(self):
        """Count related growth tracking records"""
        for flock in self:
            flock.growth_tracking_count = self.env['poultry.growth.tracking'].search_count([
                ('flock_id', '=', flock.id)
            ])

    def _compute_record_counts(self):
        """Compute counts for feed, medicine, and weighing records"""
        for flock in self:
            # Count only brooding phase records (not linked to growth tracking)
            flock.feed_consumption_count = self.env['poultry.feed.consumption'].search_count([
                ('flock_id', '=', flock.id),
                ('growth_tracking_id', '=', False)
            ])
            flock.medicine_usage_count = self.env['poultry.medicine.usage'].search_count([
                ('flock_id', '=', flock.id),
                ('growth_tracking_id', '=', False)
            ])
            flock.weighing_count = self.env['poultry.weighing'].search_count([
                ('flock_id', '=', flock.id),
                ('growth_tracking_id', '=', False)
            ])

    def action_start_growing(self):
        """Mark flock as growing"""
        if self.initial_weight <= 0:
            raise ValidationError(_('A flock can not have initial weight less than or equal to zero.'))
        if self.target_weight <= self.initial_weight:
            raise ValidationError(_('Target Weight must be greater than Initial Weight.'))
        
        self.ensure_one()
        self.state = 'growing'

    def action_mark_ready(self):
        """Open wizard to select poultry location and create internal transfer"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfer Flock'),
            'res_model': 'flock.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_flock_id': self.id,
            }
        }

    def action_close(self):
        """Close the flock"""
        self.ensure_one()
        self.state = 'closed'

    def action_view_purchase_order(self):
        """Open the related purchase order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Order'),
            'res_model': 'purchase.order',
            'res_id': self.purchase_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_picking(self):
        """Open the related stock picking"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_mortality_records(self):
        """Open the related scrap orders from mortality records"""
        self.ensure_one()
        
        # Get scrap orders from mortality records
        scrap_ids = self.mortality_ids.mapped('scrap_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mortality Records'),
            'res_model': 'stock.scrap',
            'domain': [('id', 'in', scrap_ids)],
            'view_mode': 'graph,list,form',
            'target': 'current',
        }

    def action_view_transfers(self):
        """Open the related internal transfers"""
        self.ensure_one()
        
        # Get internal transfers for this flock
        transfers = self.env['stock.picking'].search([
            ('origin', '=', self.name),
            ('picking_type_id.code', '=', 'internal')
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Internal Transfers'),
            'res_model': 'stock.picking',
            'domain': [('id', 'in', transfers.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_view_growth_tracking(self):
        """Open the related growth tracking records"""
        self.ensure_one()
        
        growth_records = self.env['poultry.growth.tracking'].search([
            ('flock_id', '=', self.id)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Growth Tracking'),
            'res_model': 'poultry.growth.tracking',
            'domain': [('id', 'in', growth_records.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_view_feed(self):
        """Open feed consumption records for brooding phase"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Feed Consumption'),
            'res_model': 'poultry.feed.consumption',
            'domain': [('flock_id', '=', self.id), ('growth_tracking_id', '=', False)],
            'view_mode': 'graph,list,form',
            'target': 'current',
            'context': {'create': False},
        }

    def action_view_medicine(self):
        """Open medicine usage records for brooding phase"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Medicine Usage'),
            'res_model': 'poultry.medicine.usage',
            'domain': [('flock_id', '=', self.id), ('growth_tracking_id', '=', False)],
            'view_mode': 'graph,list,form',
            'target': 'current',
            'context': {'create': False},
        }

    def action_view_weighing(self):
        """Open weighing records for brooding phase"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Weighing Records'),
            'res_model': 'poultry.weighing',
            'domain': [('flock_id', '=', self.id), ('growth_tracking_id', '=', False)],
            'view_mode': 'graph,list,form',
            'target': 'current',
            'context': {'create': False},
        }

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name} - {record.current_quantity} birds"
            result.append((record.id, name))
        return result
