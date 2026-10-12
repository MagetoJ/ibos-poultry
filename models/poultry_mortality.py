from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryMortality(models.Model):
    _name = 'poultry.mortality'
    _description = 'Poultry Mortality Record'
    _order = 'date desc, id desc'

    flock_id = fields.Many2one(
        'poultry.flock',
        string='Flock',
        ondelete='cascade',
        index=True
    )
    poultry_location_id = fields.Many2one(
        'poultry.location',
        string='Location',
        ondelete='set null',
        compute='_compute_location_id',
        store=True,
        index=True,
        help='Location where the weighing was performed'
    )
    growth_tracking_id = fields.Many2one(
        'poultry.growth.tracking',
        string='Growth Tracking',
        ondelete='cascade',
        index=True,
        help='Link to growth tracking record if applicable'
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    age_from = fields.Integer(
        string='Age (Days)',
        help='Age of birds in days at the time of mortality'
    )
    quantity = fields.Integer(
        string='Quantity',
        required=True,
        help='Number of birds that died'
    )
    reason = fields.Selection([
        ('doa', 'Dead on Arrival'),
        ('predation', 'Predation'),
        ('disease', 'Disease'),
        ('injury', 'Injury'),
        ('culling','Culling'),
        ('climate', 'Climate/Weather'),
        ('power', 'Power Failure'),
        ('theft', 'Theft'),
        ('other', 'Other')
    ], string='Reason',
       required=True,
       default='predation'
    )
    description = fields.Text(
        string='Description',
        help='Additional details about the mortality event'
    )
    scrap_id = fields.Many2one(
        'stock.scrap',
        string='Scrap Order',
        readonly=True,
        help='Related scrap order for inventory adjustment'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processed', 'Processed')
    ], string='Status',
       default='draft',
       required=True,
       help='Processing status of the mortality record'
    )

    @api.depends('flock_id','flock_id.location_id',)
    def _compute_location_id(self):
        """Compute location_id based on flock or growth tracking"""
        for record in self:
            if record.flock_id:
                record.poultry_location_id = record.flock_id.poultry_location_id
            else:
                record.poultry_location_id = False
    @api.constrains('quantity')
    def _check_quantity(self):
        """Validate quantity"""
        for record in self:
            # if record.quantity <= 0:
            #     raise ValidationError(_('Quantity must be greater than zero.'))
            if record.flock_id and record.quantity > record.flock_id.current_quantity:
                raise ValidationError(
                    _('Quantity cannot exceed current flock quantity (%d birds).') % 
                    record.flock_id.current_quantity
                )

    
    
    def action_process(self):
        """Process mortality records by creating scrap orders"""
        for record in self:
            if record.state == 'processed':
                raise ValidationError(_('Mortality record %s is already processed.') % record.id)
            
            # Check if there's an active growth tracking for this flock
            # If so, link this mortality record to the growth tracking so
            # scrap order and consumption adjustments go to the growth phase
            if record.flock_id and not record.growth_tracking_id:
                growth_tracking = self.env['poultry.growth.tracking'].search([
                    ('flock_id', '=', record.flock_id.id),
                    ('state', 'in', ['draft', 'confirmed', 'partially_processed']),
                ], limit=1)
                if growth_tracking:
                    record.growth_tracking_id = growth_tracking.id
            
            record._create_scrap_order()
            record._adjust_future_consumption()
            record.state = 'processed'
        
        return True
    
    def unlink(self):
        """Prevent deletion of mortality records linked to scrap orders"""
        for record in self:
            if record.scrap_id:
                raise ValidationError(
                    _('Cannot delete mortality record that is linked to scrap order %s. '
                      ) % record.scrap_id.name
                )
        return super().unlink()

    def _create_scrap_order(self):
        """Create scrap order to remove dead birds from inventory"""
        self.ensure_one()
        
        # Get flock info - from either flock_id or growth_tracking_id
        flock = self.flock_id or (self.growth_tracking_id.flock_id if self.growth_tracking_id else False)
        
        if not flock or not flock.product_id or not flock.location_id:
            return
        
        # Get scrap location
        default_loss_location = self.env['stock.location'].search([
            ('is_poultry_scrap_location', '=', True),
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)

        
        if not default_loss_location:
            scrap_location = self.env['stock.location'].search([
               ('scrap_location', '=', True),
            ('company_id', 'in', [self.env.company.id, False])
            ], limit=1)

            if not scrap_location:
                return
            
        
        # Create scrap order
        origin = f'Mortality: {self.flock_id.name}' if self.flock_id else f'Mortality: {self.growth_tracking_id.name}'
        
        scrap_vals = {
            'product_id': flock.product_id.id,
            'product_uom_id': flock.product_id.uom_id.id,
            'scrap_qty': self.quantity,
            'lot_id': flock.lot_id.id if flock.lot_id else False,
            'location_id': flock.location_id.id,
            'scrap_location_id': default_loss_location.id if default_loss_location else scrap_location.id,
            'date_done': self.date,
            'origin': origin,
        }
        
        scrap = self.env['stock.scrap'].create(scrap_vals)
        self.scrap_id = scrap.id
        
        # Validate the scrap order
        if scrap.state == 'draft':
            scrap.action_validate()
        #check if scrap is validated        
        if scrap.state != 'done':
                raise ValidationError(_('Failed to validate scrap order for mortality record %s.') % self.id)

    def _adjust_future_consumption(self):
        """Adjust future feed consumption and medicine usage quantities based on mortality"""
        self.ensure_one()
        
        # Get flock info - from either flock_id or growth_tracking_id
        flock = self.flock_id or (self.growth_tracking_id.flock_id if self.growth_tracking_id else False)
        
        if not flock:
            return
        
        # Calculate the ratio of birds lost
        current_quantity = flock.current_quantity
        if current_quantity <= 0:
            return
        
        # Get the current bird count before this mortality (includes this mortality)
        previous_bird_count = current_quantity + self.quantity
        
        # Calculate adjustment ratio (e.g., if 10 birds died from 100, ratio = 90/100 = 0.9)
        adjustment_ratio = current_quantity / previous_bird_count
        
        # Adjust future feed consumption records (after mortality date)
        if self.flock_id:
            # For brooding phase (flock), use poultry.feed.consumption
            feed_domain = [
                ('date', '>=', self.date),
                ('flock_id', '=', self.flock_id.id)
            ]
            future_feed_records = self.env['poultry.feed.consumption'].search(feed_domain)
            for feed in future_feed_records:
                feed.quantity = feed.quantity * adjustment_ratio
        elif self.growth_tracking_id:
            # For growing phase (growth), use poultry.growth.feed.consumption
            feed_domain = [
                ('date', '>', self.date),
                ('growth_tracking_id', '=', self.growth_tracking_id.id)
            ]
            future_feed_records = self.env['poultry.growth.feed.consumption'].search(feed_domain)
            for feed in future_feed_records:
                feed.quantity = feed.quantity * adjustment_ratio
        # Adjust future medicine usage records (after mortality date)
        if self.flock_id:
            # For brooding phase (flock), use poultry.medicine.usage
            medicine_domain = [
                ('date', '>', self.date),
                ('flock_id', '=', self.flock_id.id)
            ]
            future_medicine_records = self.env['poultry.medicine.usage'].search(medicine_domain)
            for medicine in future_medicine_records:
                medicine.quantity = medicine.quantity * adjustment_ratio
        elif self.growth_tracking_id:
            # For growing phase (growth), use poultry.growth.medicine.usage
            medicine_domain = [
                ('date', '>', self.date),
                ('growth_tracking_id', '=', self.growth_tracking_id.id)
            ]
            future_medicine_records = self.env['poultry.growth.medicine.usage'].search(medicine_domain)
            for medicine in future_medicine_records:
                medicine.quantity = medicine.quantity * adjustment_ratio
