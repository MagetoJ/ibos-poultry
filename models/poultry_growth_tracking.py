# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryGrowthTracking(models.Model):
    _name = 'poultry.growth.tracking'
    _description = 'Poultry Growth Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tracking_date desc, id desc'
    
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to false to archive this growth tracking record',
        tracking=True,
        invisible=True
    )
    flock_id = fields.Many2one(
        'poultry.flock',
        string='Flock',
        required=True,
        domain=[('state', '=', 'brooding')],
        tracking=True,
        help='The flock being tracked'
    )
    batch_number = fields.Char(
        string='Batch Number',
        related='flock_id.name',
        readonly=True,
        store=True
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        related='flock_id.lot_id',
        readonly=True,
        store=True,
        help='Lot/serial number for tracking this flock in inventory'
    )
    poultry_location_id = fields.Many2one(
        'poultry.location',
        string='Poultry Location',
        related='flock_id.poultry_location_id',
        readonly=True,
        store=True,
        help='Location where the flock is housed'
    )
    tracking_date = fields.Date(
        string='Tracking Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Date of the growth measurement'
    )
    initial_age_days = fields.Integer(
        string='Initial Age (Days)',
        help='Age of flock when growth tracking started'
    )
    brooding_days = fields.Integer(
        string='Days to Slaughter',
        help='Number of days spent in brooding phase (from flock)'
    )
    estimated_slaughter_date = fields.Date(
        string='Estimated Slaughter Date',
        tracking=True,
        help='Estimated date for slaughter/processing'
    )
    feed_schedule_id = fields.Many2one(
        'feed.schedule',
        string='Feed Schedule',
        tracking=True,
        help='Feeding schedule template for this growth phase'
    )
    mortality_schedule_id = fields.Many2one(
        'mortality.schedule',
        string='Mortality Schedule',
        tracking=True,
        help='Mortality schedule template for this growth phase'
    )
    weight_schedule_id = fields.Many2one(
        'weight.schedule',
        string='Weight Schedule',
        tracking=True,
        help='Weight schedule template for this growth phase'
    )
    vaccine_schedule_id = fields.Many2one(
        'vaccination.schedule',
        string='Vaccine Schedule',
        tracking=True,
        help='Vaccination schedule template for this growth phase'
    )
    maturity_age_days = fields.Integer(
        string='Maturity Age (Days)',
        tracking=True,
        help='Expected age at maturity for this flock'
    )
    age_days = fields.Integer(
        string='Current Age (Days)',
        compute='_compute_age_days',
        store=True,
        help='Current age of the flock (initial age + days since start)'
    )
    initial_quantity = fields.Integer(
        string='Initial Bird Count',
        required=True,
        tracking=True,
        help='Number of birds at start of this growth tracking period'
    )
    current_quantity = fields.Integer(
        string='Current Bird Count',
        compute='_compute_current_quantity',
        store=True,
        tracking=True,
        help='Current number of birds (initial - mortality - culled)'
    )
    mortality_count = fields.Integer(
        string='Total Deaths',
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
    sample_size = fields.Integer(
        string='Sample Size',
        compute='_compute_weight_from_weighing',
        store=True,
        help='Number of birds weighed (from latest weighing record)'
    )
    average_weight = fields.Float(
        string='Average Weight (g)',
        compute='_compute_weight_from_weighing',
        store=True,
        digits=(10, 2),
        tracking=True,
        help='Average weight per bird from latest weighing record'
    )
    current_weight = fields.Float(
        string='Current Weight (g)',
        compute='_compute_current_weight',
        store=True,
        digits=(10, 2),
        help='Current average weight from latest weighing record'
    )
    target_weight = fields.Float(
        string='Target Weight (g)',
        digits=(10, 2),
        tracking=True,
        help='Target average weight per bird'
    )
    weight_progress = fields.Float(
        string='Weight Progress (%)',
        compute='_compute_weight_progress',
        store=True,
        help='Progress towards target weight from flock initial weight'
    )
    total_weight = fields.Float(
        string='Total Sample Weight (g)',
        compute='_compute_total_weight',
        store=True,
        digits=(10, 2),
        help='Total weight of sample (sample_size × average_weight)'
    )
    daily_feed_consumption = fields.Float(
        string='Total Feed Consumed (g)',
        compute='_compute_daily_feed',
        store=True,
        digits=(10, 2),
        help='Total feed consumed on tracking date (from feed records)'
    )
    feed_per_bird = fields.Float(
        string='Feed per Bird (g)',
        compute='_compute_feed_per_bird',
        store=True,
        digits=(10, 2),
        help='Total feed consumption per bird'
    )
    fcr = fields.Float(
        string='FCR (Feed Conversion Ratio)',
        compute='_compute_fcr',
        store=True,
        digits=(10, 2),
        help='Feed Conversion Ratio - feed consumed per kg of weight gain'
    )
    mortality_today = fields.Integer(
        string='Mortality Today',
        compute='_compute_mortality_today',
        store=True,
        help='Number of birds that died on tracking date (from mortality records)'
    )
    vaccine_count = fields.Integer(
        string='Vaccine Records',
        compute='_compute_vaccine_count',
        help='Number of vaccine records for this tracking'
    )
    temperature = fields.Float(
        string='Temperature (°C)',
        digits=(5, 1),
        help='Ambient temperature in the poultry location'
    )
    humidity = fields.Float(
        string='Humidity (%)',
        digits=(5, 1),
        help='Relative humidity percentage'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional observations or notes'
    )
    feed_consumption_ids = fields.One2many(
        'poultry.growth.feed.consumption',
        'growth_tracking_id',
        string='Feed Consumption',
        help='Feed consumption records for this growth tracking'
    )
    gas_consumption_ids = fields.One2many(
        'poultry.growth.gas.consumption',
        'growth_tracking_id',
        string='Gas Consumption',
        help='Gas consumption records for this growth tracking'
    )
    medicine_usage_ids = fields.One2many(
        'poultry.growth.medicine.usage',
        'growth_tracking_id',
        string='Medicine/Vaccine Usage',
        help='Medicine and vaccine usage records for this growth tracking'
    )
    mortality_ids = fields.One2many(
        'poultry.mortality',
        'growth_tracking_id',
        string='Mortality Records',
        help='Mortality records for this growth tracking'
    )
    culling_ids = fields.One2many(
        'poultry.culling',
        'growth_tracking_id',
        string='Culling Records',
        help='Culling records for this growth tracking'
    )
    slaughter_ids = fields.One2many(
        'poultry.slaughter',
        'growth_tracking_id',
        string='Slaughter Records',
        help='Slaughter records for this growth tracking'
    )
    weighing_ids = fields.One2many(
        'poultry.weighing',
        'growth_tracking_id',
        string='Weighing Records',
        help='Weight measurement records for this growth tracking'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Active'),
        ('partially_processed', 'Partially Processed'),
        ('slaughtered', 'Closed'),
    ], string='Status',
       default='draft',
       required=True,
       tracking=True
    )
    total_slaughtered = fields.Integer(
        string='Total Slaughtered',
        store=True,
        help='Total number of birds slaughtered during this growth tracking'
    )
    
    # Cost tracking fields
    initial_flock_cost = fields.Float(
        string='Initial Flock Cost',
        digits=(10, 2),
        help='Total accumulated cost from flock at time of transfer (purchase + staging feed + staging medicine)'
    )
    growth_feed_cost = fields.Float(
        string='Growth Feed Cost',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Feed cost during growth tracking phase only'
    )
    growth_medicine_cost = fields.Float(
        string='Growth Medicine Cost',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Medicine cost during growth tracking phase only'
    )
    growth_gas_cost = fields.Float(
        string='Growth Gas Cost',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Gas cost during growth tracking phase only'
    )
    total_feed_cost = fields.Float(
        string='Total Feed Cost',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Initial flock feed cost + growth feed cost'
    )
    total_medicine_cost = fields.Float(
        string='Total Medicine Cost',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Initial flock medicine cost + growth medicine cost'
    )
    total_gas_cost = fields.Float(
        string='Total Gas Cost',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Initial flock gas cost + growth gas cost'
    )
    total_cost = fields.Float(
        string='Total Cost',
        compute='_compute_total_costs',
        store=True,
        digits=(10, 2),
        help='Initial flock cost + growth tracking costs (complete accumulated cost)'
    )
    cost_per_bird = fields.Float(
        string='Cost per Bird',
        compute='_compute_cost_per_bird',
        store=True,
        digits=(10, 2),
        help='Total cost divided by initial quantity'
    )
    
    # Smart button counts
    mortality_records_count = fields.Integer(
        string='Mortality Records',
        compute='_compute_record_counts'
    )
    feed_records_count = fields.Integer(
        string='Feed Records',
        compute='_compute_record_counts'
    )
    gas_records_count = fields.Integer(
        string='Gas Records',
        compute='_compute_record_counts'
    )
    medicine_records_count = fields.Integer(
        string='Medicine Records',
        compute='_compute_record_counts'
    )
    weighing_records_count = fields.Integer(
        string='Weighing Records',
        compute='_compute_record_counts'
    )
    processing_orders_count = fields.Integer(
        string='Processing Orders',
        compute='_compute_record_counts'
    )
    location_occupancy_pct = fields.Float(
        string='Location Occupancy %',
        compute='_compute_location_occupancy',
        help='Location occupancy as percentage of capacity'
    )
    is_ready=fields.Boolean(
        string="Ready for Slaughter",
        compute='_compute_is_ready_for_slaughter',
        store=False,
    )
    
    _sql_constraints = [
        ('initial_quantity_positive', 'CHECK(initial_quantity > 0)', 
         'Initial quantity must be greater than zero!'),
        ('sample_size_positive', 'CHECK(sample_size > 0)', 
         'Sample size must be greater than zero!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence for reference"""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('poultry.growth.tracking') or _('New')
        records = super().create(vals_list)
        
        # Generate feed consumption from schedule if available
        for record in records:
            if record.feed_schedule_id:
                record._generate_feed_consumption_from_schedule()
            
            # Generate medicine usage from vaccine schedule if available
            if record.vaccine_schedule_id:
                record._generate_medicine_usage_from_schedule()
            
            # Generate mortality from mortality schedule if available
            if record.mortality_schedule_id:
                record._generate_mortality_from_schedule()
            
            # Generate weighing from weight schedule if available
            if record.weight_schedule_id:
                record._generate_weighing_from_schedule()
        
        return records
    def action_write_off_close(self):
        self.state = 'slaughtered'
        self.flock_id.state = 'closed'
    
    def action_update_scheduled_data(self):
        """Manually trigger generation of scheduled records - auto-populates missing schedules first"""
        self.ensure_one()
        
        schedules_updated = []
        
        # Get flock_type from parent flock
        flock_type = self.flock_id.flock_type if self.flock_id else False
        
        # Auto-populate missing schedule fields based on flock_type
        if flock_type in ['hw', 'pr']:
            # Check and populate feed_schedule_id if missing
            if not self.feed_schedule_id:
                schedule_name = 'HW Schedule' if flock_type == 'hw' else 'PR Schedule'
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
                schedule_name = 'HW' if flock_type == 'hw' else 'PR'
                mortality_schedule = self.env['mortality.schedule'].search([
                    ('name', 'ilike', schedule_name)
                ], limit=1)
                if mortality_schedule:
                    self.mortality_schedule_id = mortality_schedule
                    schedules_updated.append('mortality')
            
            # Check and populate weight_schedule_id if missing
            if not self.weight_schedule_id:
                schedule_name = 'HW' if flock_type == 'hw' else 'PR'
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
        start_date = self.flock_id.date_received.date() if self.flock_id and self.flock_id.date_received else (self.flock_id.arrival_date if self.flock_id else None)
        
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

    def action_reload_all_schedules(self):
        """Force reload all schedule lines - only creates missing records (skips existing ones)"""
        self.ensure_one()
        
        # Count existing records before reload
        feed_before = len(self.feed_consumption_ids)
        medicine_before = len(self.medicine_usage_ids)
        mortality_before = len(self.mortality_ids)
        weighing_before = len(self.weighing_ids)
        
        # Regenerate all schedules (duplicate-prevention logic will skip existing records)
        if self.feed_schedule_id:
            self._generate_feed_consumption_from_schedule()
        
        if self.vaccine_schedule_id:
            self._generate_medicine_usage_from_schedule()
        
        if self.mortality_schedule_id:
            self._generate_mortality_from_schedule()
        
        if self.weight_schedule_id:
            self._generate_weighing_from_schedule()
        
        # Count new records created
        feed_added = len(self.feed_consumption_ids) - feed_before
        medicine_added = len(self.medicine_usage_ids) - medicine_before
        mortality_added = len(self.mortality_ids) - mortality_before
        weighing_added = len(self.weighing_ids) - weighing_before
        
        total_added = feed_added + medicine_added + mortality_added + weighing_added
        
        # Build message
        details = []
        if feed_added > 0:
            details.append(f'{feed_added} feed record(s)')
        if medicine_added > 0:
            details.append(f'{medicine_added} medicine record(s)')
        if mortality_added > 0:
            details.append(f'{mortality_added} mortality record(s)')
        if weighing_added > 0:
            details.append(f'{weighing_added} weighing record(s)')
        
        if total_added > 0:
            message = f"Successfully loaded {total_added} missing schedule line(s): {', '.join(details)}"
            msg_type = 'success'
        else:
            message = "All schedule lines are already loaded. No new records created."
            msg_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Schedules Reloaded'),
                'message': _(message),
                'type': msg_type,
                'sticky': False,
            }
        }

    def _generate_feed_consumption_from_schedule(self):
        """Generate feed consumption records from the selected feed schedule (only for ages > brooding_days)"""
        self.ensure_one()
        
        if not self.feed_schedule_id:
            return
        
        # Get the schedule lines, sorted by age
        schedule_lines = self.feed_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate dates from flock arrival date + age
        flock_arrival_date = self.flock_id.arrival_date
        
        # Create feed consumption records for each schedule line
        FeedConsumption = self.env['poultry.growth.feed.consumption']
        
        for line in schedule_lines:
            # Only load feed schedules for ages GREATER than brooding period (grow-out phase)
            if self.brooding_days and line.age_from <= (self.brooding_days - 1):
                continue
            
            # Skip ages before or at the bird's initial age (for birds received at older ages like 21-day birds)
            if line.age_from <= self.initial_age_days:
                continue
            
            # Calculate the date for this age (directly from arrival date + age)
            consumption_date = fields.Date.add(flock_arrival_date, days=(line.age_from- (self.initial_age_days+1)))
            
            # Calculate total quantity (quantity per bird * current quantity)
            total_quantity = line.quantity_per_bird * self.current_quantity
            
            # Check if a feed consumption record already exists for this date and product
            existing = FeedConsumption.search([
                ('growth_tracking_id', '=', self.id),
                ('date', '=', consumption_date),
                ('product_id', '=', line.feed_product_id.id)
            ], limit=1)
            
            if not existing:
                # Create feed consumption record
                FeedConsumption.create({
                    'growth_tracking_id': self.id,
                    'date': consumption_date,
                    'age_from': line.age_from,
                    'product_id': line.feed_product_id.id,
                    'cost_per_unit': line.feed_product_id.standard_price,
                    'quantity': total_quantity,
                    'notes': f'Auto-generated from {self.feed_schedule_id.name} (Age: {line.age_from} days)'
                })

    def _generate_medicine_usage_from_schedule(self):
        """Generate medicine usage records from the selected vaccine schedule (only for ages > brooding_days)"""
        self.ensure_one()
        
        if not self.vaccine_schedule_id:
            return
        
        # Get the schedule lines
        schedule_lines = self.vaccine_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate dates from flock arrival date + age
        flock_arrival_date = self.flock_id.date_received.date() if self.flock_id.date_received else self.flock_id.arrival_date
        
        # Create medicine usage records for each schedule line
        MedicineUsage = self.env['poultry.growth.medicine.usage']
        
        for line in schedule_lines:
            # Only load vaccine schedules for ages GREATER than brooding period (grow-out phase)
            if self.brooding_days and line.age_from <= (self.brooding_days - 1):
                continue
            
            # Skip ages before or at the bird's initial age (for birds received at older ages like 21-day birds)
            if line.age_from <= self.initial_age_days:
                continue
            
            # Calculate the date for this age (directly from arrival date + age)
            administration_date = fields.Date.add(flock_arrival_date, days=(line.age_from- (self.initial_age_days+1)))
            
            # Calculate total quantity (quantity per bird * current quantity)
            total_quantity = line.quantity_per_bird * self.current_quantity
            
            # Check if a medicine usage record already exists for this date and product
            existing = MedicineUsage.search([
                ('growth_tracking_id', '=', self.id),
                ('date', '=', administration_date),
                ('product_id', '=', line.vaccine_product_id.id)
            ], limit=1)
            
            if not existing:
                # Create medicine usage record
                MedicineUsage.create({
                    'growth_tracking_id': self.id,
                    'date': administration_date,
                    'product_id': line.vaccine_product_id.id,
                    'cost_per_unit': line.vaccine_product_id.standard_price,
                    'quantity': total_quantity,
                    'age_from': line.age_from,
                    'purpose': line.purpose or f'{line.vaccine_product_id.name} administration',
                    'notes': f'Auto-generated from {self.vaccine_schedule_id.name} (Age: {line.age_from} days)'
                })

    def _generate_mortality_from_schedule(self):
        """Generate expected mortality records from the selected mortality schedule (only for ages > brooding_days)"""
        self.ensure_one()
        
        if not self.mortality_schedule_id:
            return
        
        # Get the schedule lines
        schedule_lines = self.mortality_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate dates from flock arrival date + age
        flock_arrival_date = self.flock_id.date_received.date() if self.flock_id.date_received else self.flock_id.arrival_date
        
        # Track cumulative quantity for mortality calculation
        current_quantity = self.initial_quantity
        
        # Create mortality records for each schedule line
        Mortality = self.env['poultry.mortality']
        
        for line in schedule_lines:
            # Only load mortality schedules for ages GREATER than brooding period (grow-out phase)
            if self.brooding_days and line.age_from <= (self.brooding_days - 1):
                continue
            
            # Skip ages before or at the bird's initial age (for birds received at older ages like 21-day birds)
            if line.age_from <= self.initial_age_days:
                continue
            
            # Calculate the date for this age
            mortality_date = fields.Date.add(flock_arrival_date, days=(line.age_from - (self.initial_age_days + 1)))
            
            # Calculate expected mortality quantity based on rate percentage
            # mortality_rate is in percentage, so divide by 100
            expected_mortality = (line.mortality_rate / 100) * current_quantity
            
            # Update current quantity for next calculation
            current_quantity -= expected_mortality
            
            # Check if a mortality record already exists for this date
            existing = Mortality.search([
                ('growth_tracking_id', '=', self.id),
                ('date', '=', mortality_date),
                ('reason', '=', 'disease')  # Default reason for scheduled mortality
            ], limit=1)
            
            if not existing:
                # Create mortality record
                Mortality.create({
                    'growth_tracking_id': self.id,
                    'date': mortality_date,
                    'age_from': line.age_from,
                    'quantity': expected_mortality,
                    'reason': 'disease',
                    'description': ''
                })

    def _generate_weighing_from_schedule(self):
        """Generate expected weighing records from the selected weight schedule (only for ages > brooding_days)"""
        self.ensure_one()
        
        if not self.weight_schedule_id:
            return
        
        # Get the schedule lines
        schedule_lines = self.weight_schedule_id.line_ids.sorted('age_from')
        
        if not schedule_lines:
            return
        
        # Calculate dates from flock arrival date + age
        flock_arrival_date = self.flock_id.date_received.date() if self.flock_id.date_received else self.flock_id.arrival_date
        
        # Create weighing records for each schedule line
        Weighing = self.env['poultry.weighing']
        
        for line in schedule_lines:
            # Only load weighing schedules for ages GREATER than brooding period (grow-out phase)
            if self.brooding_days and line.age_from <= (self.brooding_days - 1):
                continue
            
            # Skip ages before or at the bird's initial age (for birds received at older ages like 21-day birds)
            if line.age_from <= self.initial_age_days:
                continue
            
            # Calculate the date for this age
            weighing_date = fields.Date.add(flock_arrival_date, days=(line.age_from - (self.initial_age_days + 1)))
            
            # Check if a weighing record already exists for this date
            existing = Weighing.search([
                ('growth_tracking_id', '=', self.id),
                ('weighing_date', '=', weighing_date)
            ], limit=1)
            
            if not existing:
                # Create weighing record
                Weighing.create({
                    'growth_tracking_id': self.id,
                    'weighing_date': weighing_date,
                    'age_from': line.age_from,
                    'sample_size': 10,  # Default sample size
                    'average_weight': line.expected_weight,
                    'notes': ''
                })

    @api.depends('flock_id', 'flock_id.date_received', 'tracking_date', 'initial_age_days')
    def _compute_age_days(self):
        """Calculate current physical age based on initial age plus days passed since receipt"""
        for record in self:
            if record.flock_id and record.flock_id.date_received and record.tracking_date:
                # Physical age = initial age + days since receipt
                received_date = record.flock_id.date_received.date()
                delta = record.tracking_date - received_date
                days_since_receipt = delta.days
                
                # Add initial age to get physical age
                record.age_days = (record.initial_age_days or 0) + days_since_receipt
            elif record.initial_age_days:
                # Only initial age known
                record.age_days = record.initial_age_days
            else:
                record.age_days = 0

    @api.depends('current_weight', 'target_weight', 'estimated_slaughter_date', 'state')
    def _compute_is_ready_for_slaughter(self):
        """Determine if flock is ready for slaughter based on weight or date"""
        for record in self:
            if record.state in ['confirmed', 'partially_processed']:
                weight_ready = record.current_weight >= record.target_weight if record.target_weight else False
                date_ready = record.estimated_slaughter_date and record.estimated_slaughter_date <= fields.Date.today()
                record.is_ready = weight_ready or date_ready
            else:
                record.is_ready = False

    @api.depends('initial_quantity', 'mortality_ids.quantity', 'culling_ids.quantity', 'culling_ids.state', 'slaughter_ids.quantity_slaughtered')
    def _compute_current_quantity(self):
        """Calculate current quantity based on mortality, culling and slaughter records"""
        for record in self:
            # Deaths from mortality records
            dead_count = sum(record.mortality_ids.mapped('quantity'))
            
            # Culled birds that are still culled (temporarily removed)
            culled_count = sum(
                culling.quantity 
                for culling in record.culling_ids 
                if culling.state == 'culled'
            )
            
            # Culled birds that died
            culled_dead_count = sum(
                culling.quantity 
                for culling in record.culling_ids 
                if culling.state == 'dead'
            )
            
            # Slaughtered birds
            slaughtered_count = sum(record.slaughter_ids.mapped('quantity_slaughtered'))
            
            # Current quantity = initial - deaths - still culled - culled dead - slaughtered
            record.current_quantity = record.initial_quantity - dead_count - culled_count - culled_dead_count - slaughtered_count

    @api.depends('initial_quantity', 'mortality_ids.quantity', 'culling_ids.quantity', 'culling_ids.state')
    def _compute_mortality(self):
        """Calculate mortality statistics"""
        for record in self:
            # Total dead = mortality records + culled dead
            dead_from_mortality = sum(record.mortality_ids.mapped('quantity'))
            dead_from_culling = sum(
                culling.quantity 
                for culling in record.culling_ids 
                if culling.state == 'dead'
            )
            record.mortality_count = dead_from_mortality + dead_from_culling
            
            if record.initial_quantity > 0:
                record.mortality_rate = (record.mortality_count / record.initial_quantity) * 100
            else:
                record.mortality_rate = 0.0

    @api.depends('weighing_ids', 'weighing_ids.average_weight', 'weighing_ids.sample_size', 'weighing_ids.weighing_date')
    def _compute_weight_from_weighing(self):
        """Get weight data from latest weighing record"""
        for record in self:
            if record.weighing_ids:
                # Get the latest weighing record by date
                # Use create_date as secondary sort for unsaved records
                latest = record.weighing_ids.sorted(lambda w: w.weighing_date, reverse=True)[0]
                record.sample_size = latest.sample_size
                record.average_weight = latest.average_weight
            else:
                record.sample_size = 0
                record.average_weight = 0.0
    
    @api.depends('weighing_ids', 'weighing_ids.average_weight', 'weighing_ids.weighing_date')
    def _compute_current_weight(self):
        """Get current weight from latest weighing record with non-zero weight"""
        for record in self:
            if record.weighing_ids:
                # Filter out weighing records with 0 weight
                non_zero_weighings = record.weighing_ids.filtered(lambda w: w.average_weight > 0)
                if non_zero_weighings:
                    # Get the latest weighing record by date with non-zero weight
                    latest = non_zero_weighings.sorted(lambda w: w.weighing_date, reverse=True)[0]
                    record.current_weight = latest.average_weight
                else:
                    # If all weighing records have 0 weight, use 0
                    record.current_weight = 0.0
            else:
                record.current_weight = 0.0
    
    @api.depends('feed_consumption_ids', 'feed_consumption_ids.quantity', 'feed_consumption_ids.date', 'tracking_date')
    def _compute_daily_feed(self):
        """Calculate total feed consumed on tracking date"""
        for record in self:
            feed_records = record.feed_consumption_ids.filtered(lambda f: f.date == record.tracking_date)
            record.daily_feed_consumption = sum(feed_records.mapped('quantity'))
    
    @api.depends('mortality_ids', 'mortality_ids.quantity', 'mortality_ids.date', 'tracking_date')
    def _compute_mortality_today(self):
        """Calculate total mortality on tracking date"""
        for record in self:
            mortality_records = record.mortality_ids.filtered(lambda m: m.date == record.tracking_date)
            record.mortality_today = sum(mortality_records.mapped('quantity'))
    
    @api.depends('medicine_usage_ids')
    def _compute_vaccine_count(self):
        """Count vaccine/medicine records"""
        for record in self:
            record.vaccine_count = len(record.medicine_usage_ids)
    
    @api.depends('sample_size', 'average_weight')
    def _compute_total_weight(self):
        """Calculate total sample weight"""
        for record in self:
            record.total_weight = record.sample_size * record.average_weight

    @api.depends('flock_id', 'flock_id.initial_weight', 'current_weight', 'target_weight')
    def _compute_weight_progress(self):
        """Calculate weight progress percentage"""
        for record in self:
            if record.target_weight and record.flock_id and record.flock_id.initial_weight:
                initial = record.flock_id.initial_weight
                if record.target_weight > initial:
                    weight_gained = record.current_weight - initial
                    target_gain = record.target_weight - initial
                    record.weight_progress = (weight_gained / target_gain) * 100 if target_gain > 0 else 0.0
                else:
                    record.weight_progress = 0.0
            else:
                record.weight_progress = 0.0

    @api.depends('feed_consumption_ids.total_cost', 'feed_consumption_ids.landed_cost_id', 'feed_consumption_ids.stock_move_id', 'medicine_usage_ids.total_cost', 'medicine_usage_ids.landed_cost_id', 'medicine_usage_ids.stock_move_id', 'gas_consumption_ids.total_cost', 'gas_consumption_ids.landed_cost_id', 'gas_consumption_ids.stock_move_id', 'initial_flock_cost', 'flock_id.total_feed_cost', 'flock_id.total_medicine_cost', 'flock_id.total_gas_cost')
    def _compute_total_costs(self):
        """Calculate total costs including initial flock cost + growth tracking costs (only processed records)"""
        for record in self:
            # Growth phase costs only - only sum records that have been processed (have both landed_cost_id and stock_move_id)
            processed_feed = record.feed_consumption_ids.filtered(lambda r: r.landed_cost_id or r.stock_move_id)
            processed_medicine = record.medicine_usage_ids.filtered(lambda r: r.landed_cost_id or r.stock_move_id)
            processed_gas = record.gas_consumption_ids.filtered(lambda r: r.landed_cost_id or r.stock_move_id)
            
            record.growth_feed_cost = sum(processed_feed.mapped('total_cost'))
            record.growth_medicine_cost = sum(processed_medicine.mapped('total_cost'))
            record.growth_gas_cost = sum(processed_gas.mapped('total_cost'))
            
            # If initial_flock_cost is set, use it. Otherwise, get from flock
            if record.initial_flock_cost:
                initial_cost = record.initial_flock_cost
            elif record.flock_id:
                initial_cost = record.flock_id.total_cost
            else:
                initial_cost = 0.0
            
            # Total accumulated costs
            record.total_feed_cost = (record.flock_id.total_feed_cost if record.flock_id else 0.0) + record.growth_feed_cost
            record.total_medicine_cost = (record.flock_id.total_medicine_cost if record.flock_id else 0.0) + record.growth_medicine_cost
            record.total_gas_cost = (record.flock_id.total_gas_cost if record.flock_id else 0.0) + record.growth_gas_cost
            record.total_cost = initial_cost + record.growth_feed_cost + record.growth_medicine_cost + record.growth_gas_cost

    @api.depends('total_cost', 'initial_quantity')
    def _compute_cost_per_bird(self):
        """Calculate cost per bird based on initial quantity"""
        for record in self:
            if record.initial_quantity > 0:
                record.cost_per_bird = record.total_cost / record.initial_quantity
            else:
                record.cost_per_bird = 0.0

    @api.depends('daily_feed_consumption', 'current_quantity')
    def _compute_feed_per_bird(self):
        """Calculate feed per bird"""
        for record in self:
            if record.current_quantity > 0:
                record.feed_per_bird = record.daily_feed_consumption / record.current_quantity
            else:
                record.feed_per_bird = 0.0

    @api.depends('flock_id', 'flock_id.initial_weight', 'current_weight', 'feed_consumption_ids', 'feed_consumption_ids.quantity', 'tracking_date')
    def _compute_fcr(self):
        """Calculate Feed Conversion Ratio
        FCR = Total Feed Consumed (g) / Total Weight Gain (g)
        Lower FCR is better (less feed per kg of gain)
        """
        for record in self:
            if not record.flock_id or not record.current_weight or record.current_weight <= 0:
                record.fcr = 0.0
                continue
            
            # Determine starting weight
            if record.flock_id.initial_weight > 0:
                start_weight = record.flock_id.initial_weight
            else:
                record.fcr = 0.0
                continue
            
            # Calculate weight gain per bird
            weight_gain_per_bird = record.current_weight - start_weight
            
            if weight_gain_per_bird <= 0:
                record.fcr = 0.0
                continue
            
            # Calculate total weight gain for the entire flock
            total_weight_gain = weight_gain_per_bird * record.current_quantity
            
            if total_weight_gain <= 0:
                record.fcr = 0.0
                continue
            
            # Get ALL feed consumption for this flock (brooding + growth)
            # Include feed from flock's brooding phase
            brooding_feed = self.env['poultry.feed.consumption'].search([
                ('flock_id', '=', record.flock_id.id),
                ('growth_tracking_id', '=', False)
            ])
            
            # Plus feed from growth tracking phase
            growth_feed = record.feed_consumption_ids
            
            total_feed = sum(brooding_feed.mapped('quantity')) + sum(growth_feed.mapped('quantity'))
            
            # Calculate FCR
            if total_feed > 0:
                record.fcr = total_feed / total_weight_gain
            else:
                record.fcr = 0.0
    #prevent deleting growth tracking records that are linked to other records
    def unlink(self):
        for tracking in self:
            if tracking.mortality_ids or tracking.culling_ids or tracking.weighing_ids or tracking.feed_consumption_ids or tracking.medicine_usage_ids or tracking.slaughter_ids:
                raise ValidationError(_('Cannot delete growth tracking %s as it has linked records.') % tracking.name)
            
        return super().unlink()

    def action_confirm(self):
        """Confirm the growth tracking record"""
        if self.target_weight <= self.average_weight:
            raise ValidationError(_('Target Weight must be greater than Flock Initial Weight.'))
        self.ensure_one()
        self.state = 'confirmed'

    def action_draft(self):
        """Set back to draft"""
        self.ensure_one()
        self.state = 'draft'
    
    def action_create_processing_order(self):
        """Open wizard to create processing order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Processing Order',
            'res_model': 'growth.slaughter.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_growth_tracking_id': self.id,
            }
        }
    def action_process_early(self):
        """Open wizard to create early processing order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Early Processing Order',
            'res_model': 'growth.slaughter.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_growth_tracking_id': self.id,
            }
        }
    
    def action_complete_slaughter(self):
        """Mark growth tracking as completed (slaughtered) and close flock"""

        diff = self.initial_quantity - self.current_quantity

        all_processed = (
            self.current_quantity == 0 or
            (self.total_slaughtered + diff) == self.initial_quantity
        )

        if not all_processed:
            raise ValidationError(_(
                'Cannot close growth tracking. Not all birds have been processed. '
                '%d out of %d birds slaughtered.'
            ) % (diff, self.initial_quantity))

        self.state = 'slaughtered'
        self.flock_id.state = 'closed'
    
    def action_view_flock(self):
        """Open the related flock form"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Flock',
            'res_model': 'poultry.flock',
            'res_id': self.flock_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_location(self):
        """Open the poultry location form"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Poultry Location',
            'res_model': 'poultry.location',
            'res_id': self.poultry_location_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    

    @api.depends('mortality_ids', 'feed_consumption_ids', 'gas_consumption_ids', 'medicine_usage_ids', 'weighing_ids')
    def _compute_record_counts(self):
        """Compute counts for smart buttons"""
        for record in self:
            record.mortality_records_count = len(record.mortality_ids.filtered(lambda m: m.scrap_id))
            record.feed_records_count = len(record.feed_consumption_ids)
            record.gas_records_count = len(record.gas_consumption_ids)
            record.medicine_records_count = len(record.medicine_usage_ids)
            record.weighing_records_count = len(record.weighing_ids)
            # Count manufacturing orders linked to this growth tracking
            record.processing_orders_count = self.env['mrp.production'].search_count([
                ('growth_tracking_id', '=', record.id)
            ])

    @api.depends('poultry_location_id', 'poultry_location_id.current_occupancy', 'poultry_location_id.capacity')
    def _compute_location_occupancy(self):
        """Compute location occupancy percentage"""
        for record in self:
            if record.poultry_location_id and record.poultry_location_id.capacity > 0:
                occupancy = record.poultry_location_id.current_occupancy
                capacity = record.poultry_location_id.capacity
                record.location_occupancy_pct = (occupancy / capacity) * 100
            else:
                record.location_occupancy_pct = 0.0

    def action_view_mortality(self):
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
            'context': {'create': False},
        }

    def action_view_feed(self):
        """Open feed consumption records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Feed Consumption'),
            'res_model': 'poultry.feed.consumption',
            'domain': [('growth_tracking_id', '=', self.id)],
            'view_mode': 'graph,list,form',
            'target': 'current',
            'context': {'default_growth_tracking_id': self.id, 'create': False},
        }

    def action_view_gas(self):
        """Open gas consumption records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Gas Consumption'),
            'res_model': 'poultry.gas.consumption',
            'domain': [('growth_tracking_id', '=', self.id)],
            'view_mode': 'graph,list,form',
            'target': 'current',
            'context': {'default_growth_tracking_id': self.id, 'create': False},
        }

    def action_view_medicine(self):
        """Open medicine usage records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Medicine Usage'),
            'res_model': 'poultry.medicine.usage',
            'domain': [('growth_tracking_id', '=', self.id)],
            'view_mode': 'graph,list,form',
            'target': 'current',
            'context': {'create': False},
        }

    def action_view_weighing(self):
        """Open weighing records"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Weighing Records'),
            'res_model': 'poultry.weighing',
            'domain': [('growth_tracking_id', '=', self.id)],
            'view_mode': 'graph,list,form',
            'target': 'current',
            'context': {'create': False},
        }

    def action_view_processing_orders(self):
        """Open manufacturing orders (processing orders)"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Processing Orders'),
            'res_model': 'mrp.production',
            'domain': [('growth_tracking_id', '=', self.id)],
            'view_mode': 'list,kanban,form',
            'target': 'current',
            'context': {'default_growth_tracking_id': self.id},
        }

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            name = f"{record.name} - {record.batch_number} ({record.tracking_date})"
            result.append((record.id, name))
        return result
    
    @api.model
    def _cron_close_completed_growth_tracking(self):
        """
        Maintenance cron to auto-close growth tracking records that are stuck in 
        'partially_processed' state but have no birds left (current_quantity = 0).
        
        This handles edge cases where the MO is completed manually and the automatic
        state transition doesn't trigger.
        
        IMPORTANT: This cron is disabled by default. Enable manually if needed.
        """
        # Find growth tracking records that might be stuck
        potentially_stuck = self.search([
            ('state', '=', 'partially_processed')
        ])
        
        closed_count = 0
        for record in potentially_stuck:
            # Force recompute of current_quantity
            record.invalidate_recordset(['current_quantity'])
            
            # Double-check that current quantity is actually 0
            if record.current_quantity != 0:
                continue
            
            # Calculate total slaughtered from all linked MOs
            completed_mos = self.env['mrp.production'].search([
                ('growth_tracking_id', '=', record.id),
                ('state', '=', 'done')
            ])
            total_slaughtered = sum(completed_mos.mapped('live_bird_count'))
            
            if total_slaughtered > 0:
                record.total_slaughtered = total_slaughtered
                record.action_complete_slaughter()
                record.message_post(
                    body=_(
                        'Automatically closed by maintenance cron: All %d birds processed, '
                        'current quantity is 0.'
                    ) % total_slaughtered
                )
                closed_count += 1
        
        return True
