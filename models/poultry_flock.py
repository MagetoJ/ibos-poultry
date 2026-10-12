# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


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
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to false to archive this flock',
        invisible=True
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
        string='Growth Location',
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
    arrival_date = fields.Date(
        string='Arrival Date',
        compute='_compute_arrival_date',
        store=True,
        help='Date when chicks arrived (same as receipt date)'
    )
    estimated_end_of_brooding = fields.Date(
        string='Estimated End of Brooding',
        compute='_compute_arrival_date',
        store=True,
        readonly=True,
        help='Estimated date when brooding period will end (default: 10 days after arrival)',
        
    )
    estimated_slaughter_date = fields.Date(
        string='Estimated Slaughter Date',
        compute='_compute_arrival_date',
        store=True,
        readonly=True,
        help='Estimated date for slaughter/processing',
        
    )
    brooding_days = fields.Integer(
        string='Brooding Days',
        compute='_compute_staging_days',
        store=True,
        help='Number of days in brooding period'
    )
    growing_days = fields.Integer(
        string='Growing Days',
        compute='_compute_staging_days',
        store=True,
        help='Number of days from end of brooding to slaughter'
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
        domain="[('growth_tracking_id', '=', False)]",
        string='Feed Consumption',
        help='Feed consumption records for this flock'
    )
    gas_consumption_ids = fields.One2many(
        'poultry.gas.consumption',
        'flock_id',
        domain="[('growth_tracking_id', '=', False)]",
        string='Gas Consumption',
        help='Gas consumption records for this flock'
    )
    medicine_usage_ids = fields.One2many(
        'poultry.medicine.usage',
        'flock_id',
        string='Medicine/Vaccine Usage',
        domain="[('growth_tracking_id', '=', False)]",
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
    gas_consumption_count = fields.Integer(
        string='Gas Records',
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

    flock_type = fields.Selection([
            ('select', 'Select Type'),
            ('hw', 'Higher Welfare'),
            ('pr', 'Pasture Raised'),
        ], string='Flock Type',
        required=True,
        tracking=True,
        default='select',
        help='Type of poultry flock'
        )
    
    feed_schedule_id = fields.Many2one(
        'feed.schedule',
        string='Feed Schedule',
        tracking=True,
        help='Feeding schedule template for this flock'
    )
    
    mortality_schedule_id = fields.Many2one(
        'mortality.schedule',
        string='Mortality Schedule',
        tracking=True,
        help='Mortality schedule template for this flock'
    )
    
    weight_schedule_id = fields.Many2one(
        'weight.schedule',
        string='Weight Schedule',
        tracking=True,
        help='Weight schedule template for this flock'
    )
    
    vaccine_schedule_id = fields.Many2one(
        'vaccination.schedule',
        string='Vaccine Schedule',
        tracking=True,
        help='Vaccination schedule template for this flock'
    )
    
    bird_age = fields.Selection([
        ('select', 'Select'),
        ('0', '0 Days (Day-old chicks)'),
        ('21', '21 Days (Grown birds)')
    ], string='Bird Age at Receipt',
        required=True,
        default='select',
        tracking=True,
        help='Age of birds when received. 0 for day-old chicks, 21 for grown birds that skip brooding'
    )

    @api.onchange('flock_type')
    def _onchange_flock_type(self):
        """Auto-populate feed schedule and vaccine schedule based on flock type"""
        if self.flock_type == 'hw':
            # Find HW Schedule
            schedule = self.env['feed.schedule'].search([
                ('name', '=', 'HW Schedule')
            ], limit=1)
            self.feed_schedule_id = schedule.id if schedule else False
            # Find HW Mortality Schedule
            mortality_schedule = self.env['mortality.schedule'].search([
                ('name', 'ilike', 'HW')
            ], limit=1)
            self.mortality_schedule_id = mortality_schedule.id if mortality_schedule else False
            # Find HW Weight Schedule
            weight_schedule = self.env['weight.schedule'].search([
                ('name', 'ilike', 'HW')
            ], limit=1)
            self.weight_schedule_id = weight_schedule.id if weight_schedule else False
        elif self.flock_type == 'pr':
            # Find PR Schedule
            schedule = self.env['feed.schedule'].search([
                ('name', '=', 'PR Schedule')
            ], limit=1)
            self.feed_schedule_id = schedule.id if schedule else False
            # Find PR Mortality Schedule
            mortality_schedule = self.env['mortality.schedule'].search([
                ('name', 'ilike', 'PR')
            ], limit=1)
            self.mortality_schedule_id = mortality_schedule.id if mortality_schedule else False
            # Find PR Weight Schedule
            weight_schedule = self.env['weight.schedule'].search([
                ('name', 'ilike', 'PR')
            ], limit=1)
            self.weight_schedule_id = weight_schedule.id if weight_schedule else False
        else:
            # For 'select' type, clear the schedule
            self.feed_schedule_id = False
            self.mortality_schedule_id = False
            self.weight_schedule_id = False
        
        # Auto-populate vaccine schedule for all flock types (default: Vaccination Schedule)
        if self.flock_type in ['hw', 'pr']:
            vaccine_schedule = self.env.ref('ibos_poultry.vaccination_schedule_broiler', raise_if_not_found=False)
            self.vaccine_schedule_id = vaccine_schedule.id if vaccine_schedule else False
        else:
            self.vaccine_schedule_id = False


    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence for batch number and auto-trigger workflow based on bird age"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('poultry.flock') or 'New'
        
        flocks = super().create(vals_list)
        
        # Auto-trigger workflow based on bird age
        for flock in flocks:
            if flock.state == 'received':  # Only for newly received flocks
                try:
                    # Always call action_start_growing for proper procedure
                    flock.action_start_growing()
                except ValidationError:
                    # If validation fails, user will need to set required fields manually
                    pass
        
        return flocks

    @api.depends('date_received')
    def _compute_age(self):
        """Calculate age in days"""
        for flock in self:
            if flock.date_received:
                delta = fields.Datetime.now() - flock.date_received
                flock.age_days = delta.days
            else:
                flock.age_days = 0
    
    @api.depends('date_received', 'bird_age')
    def _compute_arrival_date(self):
        """Set arrival date to receipt date and compute dates based on bird age"""
        for flock in self:
            if flock.date_received:
                flock.arrival_date = flock.date_received.date()
                
                # Set brooding and slaughter dates based on bird age
                if flock.bird_age == '21':
                    # 21-day birds skip brooding - go directly to grow-out
                    flock.estimated_end_of_brooding = flock.arrival_date  # 0 days brooding
                    if flock.flock_type == "hw":
                        flock.estimated_slaughter_date = flock.arrival_date + timedelta(days=17)
                    elif flock.flock_type == "pr":
                        flock.estimated_slaughter_date = flock.arrival_date + timedelta(days=27)
                    else:
                        flock.estimated_slaughter_date = flock.arrival_date + timedelta(days=24)
                else:
                    # Day-old chicks need brooding period
                    flock.estimated_end_of_brooding = flock.arrival_date + timedelta(days=18)
                    if flock.flock_type == "hw":
                        flock.estimated_slaughter_date = flock.estimated_end_of_brooding + timedelta(days=17)
                    elif flock.flock_type == "pr":
                        flock.estimated_slaughter_date = flock.estimated_end_of_brooding + timedelta(days=27)
                    else:
                        flock.estimated_slaughter_date = flock.estimated_end_of_brooding + timedelta(days=24)
            else:
                flock.arrival_date = False
                flock.estimated_end_of_brooding = False
                flock.estimated_slaughter_date = False
            
    @api.onchange('flock_type', 'bird_age')
    def _onchange_flock_type_dates(self):  
        """Set default brooding and slaughter dates based on flock type and bird age"""
        if self.date_received:
            if self.bird_age == '21':
                # 21-day birds skip brooding
                self.estimated_end_of_brooding = self.date_received.date()
                if self.flock_type == 'hw':
                    self.estimated_slaughter_date = self.estimated_end_of_brooding + timedelta(days=17)
                elif self.flock_type == 'pr':
                    self.estimated_slaughter_date = self.estimated_end_of_brooding + timedelta(days=27)
                else:
                    self.estimated_slaughter_date = self.estimated_end_of_brooding + timedelta(days=24)
            else:
                # Day-old chicks need brooding
                self.estimated_end_of_brooding = self.date_received.date() + timedelta(days=18)
                if self.flock_type == 'hw':
                    self.estimated_slaughter_date = self.estimated_end_of_brooding + timedelta(days=17)
                elif self.flock_type == 'pr':
                    self.estimated_slaughter_date = self.estimated_end_of_brooding + timedelta(days=27)
                else:
                    self.estimated_slaughter_date = self.estimated_end_of_brooding + timedelta(days=24) 
    
    @api.onchange('date_received')
    def _onchange_date_received(self):
        """Set estimated dates based on receipt date and bird age"""
        if self.date_received and not self.estimated_end_of_brooding:
            if self.bird_age == '21':
                # 21-day birds skip brooding
                self.estimated_end_of_brooding = self.date_received.date()
            else:
                # Day-old chicks need brooding
                self.estimated_end_of_brooding = self.date_received.date() + timedelta(days=18)
    
    @api.depends('arrival_date', 'estimated_end_of_brooding', 'estimated_slaughter_date', 'date_received', 'state')
    def _compute_staging_days(self):
        """Calculate brooding days, growing days, and total days"""
        for flock in self:
            today = fields.Date.today()
            
            # Brooding days (from arrival to estimated end of brooding or today if still brooding)
            if flock.arrival_date:
                if flock.estimated_end_of_brooding:
                    # Brooding period ended
                    delta = flock.estimated_end_of_brooding - flock.arrival_date
                    flock.brooding_days = max(0, delta.days)
                else:
                    # Still in brooding
                    delta = today - flock.arrival_date
                    flock.brooding_days = max(0, delta.days)
            else:
                flock.brooding_days = 0
            
            # Growing days (from end of brooding to slaughter or today if still growing)
            if flock.estimated_end_of_brooding:
                if flock.estimated_slaughter_date:
                    # Has estimated slaughter date
                    delta = flock.estimated_slaughter_date - flock.estimated_end_of_brooding
                    flock.growing_days = max(0, delta.days)
                else:
                    # Still growing, calculate from end of brooding to today
                    delta = today - flock.estimated_end_of_brooding
                    flock.growing_days = max(0, delta.days)
            else:
                flock.growing_days = 0
            

    @api.depends('weighing_ids.weighing_date', 'weighing_ids.average_weight')
    def _compute_current_weight(self):
        """Get current weight from latest weighing record (excluding zero weights)"""
        for flock in self:
            # Filter out weighing records with zero weight to avoid showing placeholder values
            non_zero_weighings = flock.weighing_ids.filtered(lambda w: w.average_weight > 0)
            latest_weighing = non_zero_weighings.sorted('weighing_date', reverse=True)[:1]
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

    @api.depends('initial_cost_per_bird', 'initial_quantity', 'feed_consumption_ids.total_cost', 'feed_consumption_ids.landed_cost_id', 'feed_consumption_ids.stock_move_id', 'medicine_usage_ids.total_cost', 'medicine_usage_ids.landed_cost_id', 'medicine_usage_ids.stock_move_id', 'gas_consumption_ids.total_cost', 'gas_consumption_ids.landed_cost_id', 'gas_consumption_ids.stock_move_id')
    def _compute_total_costs(self):
        """Calculate total costs (only including processed records with landed costs and stock moves)"""
        for flock in self:
            # Only sum costs for records that have been processed (have both landed_cost_id and stock_move_id)
            processed_feed = flock.feed_consumption_ids.filtered(lambda r: r.landed_cost_id and r.stock_move_id)
            processed_medicine = flock.medicine_usage_ids.filtered(lambda r: r.landed_cost_id and r.stock_move_id)
            processed_gas = flock.gas_consumption_ids.filtered(lambda r: r.landed_cost_id and r.stock_move_id)
            
            flock.total_feed_cost = sum(processed_feed.mapped('total_cost'))
            flock.total_medicine_cost = sum(processed_medicine.mapped('total_cost'))
            flock.total_gas_cost = sum(processed_gas.mapped('total_cost'))
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
            flock.mortality_records_count = len(flock.mortality_ids.filtered(lambda m: m.scrap_id))

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
        """Compute counts for feed, gas, medicine, and weighing records"""
        for flock in self:
            # Count only brooding phase records (not linked to growth tracking)
            flock.feed_consumption_count = self.env['poultry.feed.consumption'].search_count([
                ('flock_id', '=', flock.id),
                ('growth_tracking_id', '=', False)
            ])
            flock.gas_consumption_count = self.env['poultry.gas.consumption'].search_count([
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
        """Mark flock as growing and auto-trigger transfer wizard for 21-day birds"""
        #ensure type is selected
        for flock in self:
            if flock.bird_age == 'select':
                raise ValidationError(_('Please select a valid bird age at receipt before starting growth.'))
            
            if flock.flock_type == 'select':
                raise ValidationError(_('Please select a valid flock type before starting growth.'))
            
        if not self.estimated_end_of_brooding:
            raise ValidationError(_('Please set the Estimated End of Brooding date before starting growth.'))
        
        if not self.estimated_slaughter_date:
            raise ValidationError(_('Please set the Estimated Slaughter Date before starting growth.'))
        
        if self.initial_weight <= 0:
            raise ValidationError(_('A flock can not have initial weight less than or equal to zero.'))
        
        if self.target_weight <= self.initial_weight:
            raise ValidationError(_('Target Weight must be greater than Initial Weight.'))
        
        self.ensure_one()
        
        # Load feed consumption from schedule
        if self.feed_schedule_id:
            self._generate_feed_consumption_from_schedule()
        
        # Load medicine usage from vaccine schedule
        if self.vaccine_schedule_id:
            self._generate_medicine_usage_from_schedule()
        
        # Load mortality from mortality schedule
        if self.mortality_schedule_id:
            self._generate_mortality_from_schedule()
        
        # Load weighing from weight schedule
        if self.weight_schedule_id:
            self._generate_weighing_from_schedule()
        
        self.state = 'growing'
        
        # For 21-day birds, automatically open transfer wizard (but don't confirm)
        # if self.bird_age == '21':
        #     return self.action_mark_ready()
    
    def action_update_scheduled_data(self):
        """Manually trigger generation of scheduled records - auto-populates missing schedules first"""
        self.ensure_one()
        
        schedules_updated = []
        
        # Auto-populate missing schedule fields based on flock_type
        if self.flock_type in ['hw', 'pr']:
            # Check and populate feed_schedule_id if missing
            if not self.feed_schedule_id:
                schedule_name = 'HW Schedule' if self.flock_type == 'hw' else 'PR Schedule'
                schedule = self.env['feed.schedule'].search([('name', '=', schedule_name)], limit=1)
                if schedule:
                    self.feed_schedule_id = schedule
                    schedules_updated.append('feed')
            
            # Check and populate vaccine_schedule_id if missing
            if not self.vaccine_schedule_id:
                vaccine_schedule = self.env.ref('ibos_poultry.vaccination_schedule_broiler', raise_if_not_found=False)
                if vaccine_schedule:
                    self.vaccine_schedule_id = vaccine_schedule
                    schedules_updated.append('vaccine')
            
            # Check and populate mortality_schedule_id if missing
            if not self.mortality_schedule_id:
                schedule_name = 'HW' if self.flock_type == 'hw' else 'PR'
                mortality_schedule = self.env['mortality.schedule'].search([
                    ('name', 'ilike', schedule_name)
                ], limit=1)
                if mortality_schedule:
                    self.mortality_schedule_id = mortality_schedule
                    schedules_updated.append('mortality')
            
            # Check and populate weight_schedule_id if missing
            if not self.weight_schedule_id:
                schedule_name = 'HW' if self.flock_type == 'hw' else 'PR'
                weight_schedule = self.env['weight.schedule'].search([
                    ('name', 'ilike', schedule_name)
                ], limit=1)
                if weight_schedule:
                    self.weight_schedule_id = weight_schedule
                    schedules_updated.append('weight')
        
        # Generate records only for newly populated schedules
        if 'feed' in schedules_updated and self.feed_schedule_id:
            self._generate_feed_consumption_from_schedule()
        
        if 'vaccine' in schedules_updated and self.vaccine_schedule_id:
            self._generate_medicine_usage_from_schedule()
        
        if 'mortality' in schedules_updated and self.mortality_schedule_id:
            self._generate_mortality_from_schedule()
        
        if 'weight' in schedules_updated and self.weight_schedule_id:
            self._generate_weighing_from_schedule()
        
        # Update existing records with missing age_from (age_from = 0 or False)
        ages_updated = 0
        start_date = self.date_received.date() if self.date_received else self.arrival_date
        
        if start_date:
            # Update mortality records with age_from = 0 or False
            for mortality in self.mortality_ids.filtered(lambda m: not m.age_from):
                if mortality.date:
                    age_days = (mortality.date - start_date).days
                    mortality.age_from = age_days
                    ages_updated += 1
            
            # Update weighing records with age_from = 0 or False
            for weighing in self.weighing_ids.filtered(lambda w: not w.age_from):
                if weighing.weighing_date:
                    age_days = (weighing.weighing_date - start_date).days
                    weighing.age_from = age_days
                    ages_updated += 1
        
        if schedules_updated:
            message = f"Updated schedules: {', '.join(schedules_updated)}. Scheduled records have been generated."
            if ages_updated > 0:
                message += f" Updated {ages_updated} record(s) with missing ages."
        elif ages_updated > 0:
            message = f"Updated {ages_updated} record(s) with missing ages."
        else:
            message = "All schedules are already populated. No new records generated."
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Data Updated'),
                'message': _(message),
                'type': 'success' if (schedules_updated or ages_updated > 0) else 'info',
                'sticky': False,
            }
        }

    def _generate_feed_consumption_from_schedule(self):
        """Generate feed consumption records from the selected feed schedule"""
        self.ensure_one()
        
        # Skip feed schedule generation for 21-day birds (no brooding phase)
        if self.bird_age == '21':
            return
        
        if not self.feed_schedule_id:
            return
        
        # Get the schedule lines
        schedule_lines = self.feed_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate brooding days inline to avoid stale computed field values
        brooding_days = self.brooding_days
        
        # Calculate start date from arrival date
        start_date = self.date_received.date() if self.date_received else self.arrival_date
        
        # Create feed consumption records for each schedule line
        FeedConsumption = self.env['poultry.feed.consumption']
        
        for line in schedule_lines:
            # Only load feed schedules for ages within brooding period. Account for age 0 being the first day, so age_from > (brooding_days - 1) means it starts after brooding period ends
            if brooding_days and line.age_from > (brooding_days - 1):
                continue
            
            # Calculate the date for this age (directly from arrival date + age)
            consumption_date = fields.Date.add(start_date, days=line.age_from)
            
            # Calculate total quantity (quantity per bird * current quantity)truncate whole numbers only
            total_quantity = line.quantity_per_bird * self.current_quantity
            
            # Check if a feed consumption record already exists for this date and product
            existing = FeedConsumption.search([
                ('flock_id', '=', self.id),
                ('date', '=', consumption_date),
                ('product_id', '=', line.feed_product_id.id)
            ], limit=1)
            
            if not existing:
                max_allowed_date = self.estimated_end_of_brooding
                if consumption_date > max_allowed_date:
                    continue
                else:
                    # Create feed consumption record
                    FeedConsumption.create({
                        'flock_id': self.id,
                        'date': consumption_date,
                        'age_from': line.age_from,
                        'product_id': line.feed_product_id.id,
                        'cost_per_unit': line.feed_product_id.standard_price,
                        'quantity': total_quantity,
                        'notes': f'Auto-generated from {self.feed_schedule_id.name} (Age: {line.age_from} days)'
                    })

    def _generate_medicine_usage_from_schedule(self):
        """Generate medicine usage records from the selected vaccine schedule"""
        self.ensure_one()
        
        # Skip vaccination schedule generation for 21-day birds (no brooding phase)
        if self.bird_age == '21':
            return
        
        if not self.vaccine_schedule_id:
            return
        
        # Get the schedule lines
        schedule_lines = self.vaccine_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate brooding days inline to avoid stale computed field values
        brooding_days = self.brooding_days
        
        # Calculate start date from arrival date
        start_date = self.date_received.date() if self.date_received else self.arrival_date
        
        # Create medicine usage records for each schedule line
        MedicineUsage = self.env['poultry.medicine.usage']
        
        for line in schedule_lines:
            # Only load vaccine schedules for ages within brooding period. Account for age 0 being the first day, so age_from > (brooding_days - 1) means it starts after brooding period ends
            if brooding_days and line.age_from > (brooding_days - 1):
                continue
            
            # Calculate the date for this age (directly from arrival date + age)
            administration_date = fields.Date.add(start_date, days=line.age_from)
            
            # Calculate total quantity (quantity per bird * current quantity)
            total_quantity = line.quantity_per_bird * self.current_quantity
            
            # Check if a medicine usage record already exists for this date and product
            existing = MedicineUsage.search([
                ('flock_id', '=', self.id),
                ('date', '=', administration_date),
                ('product_id', '=', line.vaccine_product_id.id)
            ], limit=1)
            
            if not existing:
                max_allowed_date = self.estimated_end_of_brooding
                if administration_date > max_allowed_date:
                    continue
                else:
                    # Create medicine usage record
                    MedicineUsage.create({
                        'flock_id': self.id,
                        'date': administration_date,
                        'age_from': line.age_from,
                        'product_id': line.vaccine_product_id.id,
                        'cost_per_unit': line.vaccine_product_id.standard_price,
                        'quantity': total_quantity,
                        'purpose': line.purpose or f'{line.vaccine_product_id.name} administration',
                        'notes': f'Auto-generated from {self.vaccine_schedule_id.name} (Age: {line.age_from} days)'
                    })

    def _generate_mortality_from_schedule(self):
        """Generate expected mortality records from the selected mortality schedule"""
        self.ensure_one()
        
        # Skip mortality schedule generation for 21-day birds (no brooding phase)
        if self.bird_age == '21':
            return
        
        if not self.mortality_schedule_id:
            return
        
        # Get the schedule lines
        schedule_lines = self.mortality_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate brooding days inline to avoid stale computed field values
        brooding_days = self.brooding_days
        
        # Calculate start date from arrival date
        start_date = self.date_received.date() if self.date_received else self.arrival_date
        
        # Track cumulative quantity for mortality calculation
        current_quantity = self.initial_quantity
        
        # Create mortality records for each schedule line
        Mortality = self.env['poultry.mortality']
        
        for line in schedule_lines:
            # Only load mortality schedules for ages within brooding period
            if brooding_days and line.age_from > (brooding_days - 1):
                continue
            
            # Calculate the date for this age
            mortality_date = fields.Date.add(start_date, days=line.age_from)
            
            # Calculate expected mortality quantity based on rate percentage
            # mortality_rate is in percentage, so divide by 100
            expected_mortality = (line.mortality_rate / 100 * current_quantity)
            
            # Update current quantity for next calculation
            current_quantity -= expected_mortality
            
            # Check if a mortality record already exists for this date
            existing = Mortality.search([
                ('flock_id', '=', self.id),
                ('date', '=', mortality_date),
                ('reason', '=', 'disease')  # Default reason for scheduled mortality
            ], limit=1)
            
            if not existing:
                max_allowed_date = self.estimated_end_of_brooding
                if mortality_date > max_allowed_date:
                    continue
                else:
                    # Create mortality record
                    Mortality.create({
                        'flock_id': self.id,
                        'date': mortality_date,
                        'age_from': line.age_from,
                        'quantity': expected_mortality,
                        'reason': 'disease',
                        'description': ''
                    })

    def _generate_weighing_from_schedule(self):
        """Generate expected weighing records from the selected weight schedule"""
        self.ensure_one()
        
        # Skip weight schedule generation for 21-day birds (no brooding phase)
        if self.bird_age == '21':
            return
        
        if not self.weight_schedule_id:
            return
        
        # Get the schedule lines
        schedule_lines = self.weight_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate brooding days inline to avoid stale computed field values
        brooding_days = self.brooding_days
        
        # Calculate start date from arrival date
        start_date = self.date_received.date() if self.date_received else self.arrival_date
        
        # Create weighing records for each schedule line
        Weighing = self.env['poultry.weighing']
        
        for line in schedule_lines:
            # Only load weighing schedules for ages within brooding period
            if brooding_days and line.age_from > (brooding_days - 1):
                continue
            
            # Calculate the date for this age
            weighing_date = fields.Date.add(start_date, days=line.age_from)
            
            # Check if a weighing record already exists for this date
            existing = Weighing.search([
                ('flock_id', '=', self.id),
                ('weighing_date', '=', weighing_date)
            ], limit=1)
            
            if not existing:
                max_allowed_date = self.estimated_end_of_brooding
                if weighing_date > max_allowed_date:
                    continue
                
                # Create weighing record with expected weight
                Weighing.create({
                    'flock_id': self.id,
                    'weighing_date': weighing_date,
                    'age_from': line.age_from,
                    'sample_size': 10,  # Default sample size
                    'average_weight': line.expected_weight,
                    'notes': ''
                })

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
    def action_view_gas(self):
        """Open gas consumption records for brooding phase"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Gas Consumption'),
            'res_model': 'poultry.gas.consumption',
            'domain': [('flock_id', '=', self.id), ('growth_tracking_id', '=', False)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'default_flock_id': self.id},
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

    def cleanup_brooding_records(self):
        """
        Clean up feed consumption and medicine usage records that are beyond the brooding period.
        This should be called after growth tracking is created to ensure the flock only has
        records for the brooding phase.
        """
        self.ensure_one()
        
        # Calculate brooding days inline to ensure accuracy
        brooding_days = 0
        if self.arrival_date and self.estimated_end_of_brooding:
            delta = self.estimated_end_of_brooding - self.arrival_date
            brooding_days = max(0, delta.days)
        
        if not brooding_days:
            return
        
        # Get the max allowed date (end of brooding)
        max_allowed_date = self.estimated_end_of_brooding
        
        # Find and delete feed consumption records beyond brooding period
        # Only delete unprocessed records (no landed_cost_id and no stock_move_id)
        feed_to_delete = self.env['poultry.feed.consumption'].search([
            ('flock_id', '=', self.id),
            ('growth_tracking_id', '=', False),
            ('date', '>', max_allowed_date),
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
        ])
        if feed_to_delete:
            feed_to_delete.unlink()
        
        # Find and delete medicine usage records beyond brooding period
        # Only delete unprocessed records (no landed_cost_id and no stock_move_id)
        medicine_to_delete = self.env['poultry.medicine.usage'].search([
            ('flock_id', '=', self.id),
            ('growth_tracking_id', '=', False),
            ('date', '>', max_allowed_date),
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
        ])
        if medicine_to_delete:
            medicine_to_delete.unlink()
        
        # Also clean up any records where the schedule age exceeds brooding_days
        # by checking the notes field for age information
        all_flock_feed = self.env['poultry.feed.consumption'].search([
            ('flock_id', '=', self.id),
            ('growth_tracking_id', '=', False),
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
        ])
        for record in all_flock_feed:
            # Extract age from notes if available (format: "... (Age: X days)")
            if record.notes and 'Age:' in record.notes:
                try:
                    age_str = record.notes.split('Age:')[1].split('days')[0].strip()
                    age = int(age_str)
                    if age > brooding_days:
                        record.unlink()
                except (ValueError, IndexError):
                    pass
        
        all_flock_medicine = self.env['poultry.medicine.usage'].search([
            ('flock_id', '=', self.id),
            ('growth_tracking_id', '=', False),
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
        ])
        for record in all_flock_medicine:
            # Extract age from notes if available (format: "... (Age: X days)")
            if record.notes and 'Age:' in record.notes:
                try:
                    age_str = record.notes.split('Age:')[1].split('days')[0].strip()
                    age = int(age_str)
                    if age > brooding_days:
                        record.unlink()
                except (ValueError, IndexError):
                    pass
    #prevent deleting growth tracking records that are linked to other records
    def unlink(self):
        for record in self:
            if record.picking_id or record.purchase_order_id:
                raise ValidationError(_('Cannot delete a flock that is linked to other records.'))
            
        return super().unlink()

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name} - {record.current_quantity} birds"
            result.append((record.id, name))
        return result
