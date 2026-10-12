from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PoultryCulling(models.Model):
    _name = 'poultry.culling'
    _description = 'Poultry Culling Record'
    _order = 'date desc, id desc'

    flock_id = fields.Many2one(
        'poultry.flock',
        string='Flock',
        ondelete='cascade',
        index=True
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
    quantity = fields.Integer(
        string='Quantity',
        required=True,
        help='Number of birds culled'
    )
    state = fields.Selection([
        ('culled', 'Culled'),
        ('recovered', 'Recovered'),
        ('dead', 'Dead'),
    ], string='Status',
       required=True,
       default='culled',
       help='Current status of culled birds'
    )
    reason = fields.Selection([
        ('sick', 'Sick/Weak'),
        ('injury', 'Injury'),
        ('deformity', 'Deformity'),
        ('observation', 'Under Observation'),
        ('other', 'Other'),
    ], string='Culling Reason',
       required=True,
       default='sick'
    )
    description = fields.Text(
        string='Description',
        help='Additional details about the culling'
    )

    @api.constrains('quantity')
    def _check_quantity(self):
        """Validate quantity"""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    @api.model_create_multi
    def create(self, vals_list):
        """Override to adjust future feed/medicine quantities when birds are culled"""
        records = super().create(vals_list)
        for record in records:
            record._adjust_future_consumption()
        return records

    def _adjust_future_consumption(self):
        """Adjust future feed consumption and medicine usage quantities when birds are culled"""
        self.ensure_one()
        
        # Only adjust when birds are initially culled (not when marking recovered/dead)
        if self.state != 'culled':
            return
        
        # Get flock info - from either flock_id or growth_tracking_id
        flock = self.flock_id or (self.growth_tracking_id.flock_id if self.growth_tracking_id else False)
        
        if not flock:
            return
        
        # Calculate the ratio of birds lost
        current_quantity = flock.current_quantity
        if current_quantity <= 0:
            return
        
        # Get the current bird count before this culling (includes this culling)
        previous_bird_count = current_quantity + self.quantity
        
        # Calculate adjustment ratio (e.g., if 10 birds culled from 100, ratio = 90/100 = 0.9)
        adjustment_ratio = current_quantity / previous_bird_count
        
        # Adjust future feed consumption records (after culling date)
        if self.flock_id:
            # For brooding phase (flock), use poultry.feed.consumption
            feed_domain = [
                ('date', '>', self.date),
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
        
        # Adjust future medicine usage records (after culling date)
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

    def action_mark_recovered(self):
        """Mark culled birds as recovered and restore feed/medicine quantities"""
        for record in self:
            if record.state == 'culled':
                # Calculate the restoration ratio before changing state
                flock = record.flock_id or (record.growth_tracking_id.flock_id if record.growth_tracking_id else False)
                if flock:
                    current_quantity = flock.current_quantity
                    # After recovery, bird count will be current + recovered quantity
                    new_bird_count = current_quantity + record.quantity
                    # Restoration ratio (e.g., if recovering 10 birds to 90, ratio = 100/90 = 1.111)
                    restoration_ratio = new_bird_count / current_quantity if current_quantity > 0 else 1.0
                    
                    # Restore future feed consumption records
                    if record.flock_id:
                        # For brooding phase (flock), use poultry.feed.consumption
                        feed_domain = [('date', '>', record.date), ('flock_id', '=', record.flock_id.id)]
                        future_feed_records = self.env['poultry.feed.consumption'].search(feed_domain)
                        for feed in future_feed_records:
                            feed.quantity = feed.quantity * restoration_ratio
                    elif record.growth_tracking_id:
                        # For growing phase (growth), use poultry.growth.feed.consumption
                        feed_domain = [('date', '>', record.date), ('growth_tracking_id', '=', record.growth_tracking_id.id)]
                        future_feed_records = self.env['poultry.growth.feed.consumption'].search(feed_domain)
                        for feed in future_feed_records:
                            feed.quantity = feed.quantity * restoration_ratio
                    
                    # Restore future medicine usage records
                    if record.flock_id:
                        # For brooding phase (flock), use poultry.medicine.usage
                        medicine_domain = [('date', '>', record.date), ('flock_id', '=', record.flock_id.id)]
                        future_medicine_records = self.env['poultry.medicine.usage'].search(medicine_domain)
                        for medicine in future_medicine_records:
                            medicine.quantity = medicine.quantity * restoration_ratio
                    elif record.growth_tracking_id:
                        # For growing phase (growth), use poultry.growth.medicine.usage
                        medicine_domain = [('date', '>', record.date), ('growth_tracking_id', '=', record.growth_tracking_id.id)]
                        future_medicine_records = self.env['poultry.growth.medicine.usage'].search(medicine_domain)
                        for medicine in future_medicine_records:
                            medicine.quantity = medicine.quantity * restoration_ratio
                
                record.state = 'recovered'
                record.flock_id._compute_current_quantity()

    def action_mark_dead(self):
        """Mark culled birds as dead and create mortality record"""
        for record in self:
            if record.state == 'culled':
                record.state = 'dead'
                
                # Create mortality record
                self.env['poultry.mortality'].create({
                    'flock_id': record.flock_id.id,
                    'date': fields.Date.context_today(self),
                    'quantity': record.quantity,
                    'reason': 'natural_death',
                    'description': f'Culled birds that died: {record.description or record.reason}',
                })
                
                record.flock_id._compute_current_quantity()

