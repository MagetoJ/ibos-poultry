# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryGasConsumption(models.Model):
    _name = 'poultry.gas.consumption'
    _description = 'Poultry Gas Consumption'
    _rec_name = 'product_id'
    _order = 'date desc, id desc'
    _sql_constraints = [
        ('unique_flock_date', 'UNIQUE(flock_id, date, product_id)', 
         'Only one gas consumption entry per product per day is allowed for each flock!'),
    ]

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
        help='Location where gas was consumed'
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
    product_id = fields.Many2one(
        'product.product',
        string='Gas Product',
        required=True,
        domain=[('poultry_product_type', '=', 'gas')]
    )
    quantity = fields.Float(
        string='Quantity (kg)',
        required=True,
        digits=(10, 2),
        help='Gas consumed in kilograms'
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        related='product_id.uom_id'
    )
    cost_per_unit = fields.Float(
        string='Cost per Unit',
        required=True,
        digits='Product Price'
    )
    total_cost = fields.Float(
        string='Total Cost',
        compute='_compute_total_cost',
        store=True,
        digits='Product Price'
    )
    stock_move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        readonly=True,
        help='Related stock move for inventory consumption'
    )
    landed_cost_id = fields.Many2one(
        'stock.landed.cost',
        string='Landed Cost',
        readonly=True,
        help='Related landed cost for cost allocation'
    )
    notes = fields.Text(
        string='Notes'
    )

    @api.depends('flock_id','flock_id.location_id',)
    def _compute_location_id(self):
        """Compute location_id based on flock or growth tracking"""
        for record in self:
            if record.flock_id:
                record.poultry_location_id = record.flock_id.poultry_location_id
            else:
                record.poultry_location_id = False
                
    @api.constrains('flock_id', 'growth_tracking_id')
    def _check_flock_or_growth_tracking(self):
        """Ensure either flock_id or growth_tracking_id is set"""
        for record in self:
            if not record.flock_id and not record.growth_tracking_id:
                raise ValidationError(_('Either Flock or Growth Tracking must be set.'))
    
    @api.constrains('date')
    def _check_date_not_future(self):
        """Ensure date is not in the future"""
        for record in self:
            if record.date and record.date > fields.Date.context_today(record):
                raise ValidationError(_('Gas consumption date cannot be in the future.'))

    @api.constrains('quantity')
    def _check_quantity(self):
        """Validate quantity"""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        return records

    @api.depends('quantity', 'cost_per_unit')
    def _compute_total_cost(self):
        """Calculate total cost"""
        for record in self:
            record.total_cost = record.quantity * record.cost_per_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Set default cost from product"""
        if self.product_id:
            self.cost_per_unit = self.product_id.standard_price

    def _create_landed_cost(self):
        """Create landed cost to allocate gas cost to chicks"""
        self.ensure_one()
        
        # Get flock info - from either flock_id or growth_tracking_id
        flock = self.flock_id or (self.growth_tracking_id.flock_id if self.growth_tracking_id else False)
        picking = flock.picking_id if flock else False
        
        if not flock or not picking:
            return
        
        # Get the cost allocation service product
        cost_product = self.env.ref('ibos_poultry.product_poultry_cost_allocation', raise_if_not_found=False)
        if not cost_product:
            return
        
        # Create name based on context
        if self.flock_id:
            name = f'Gas: {self.product_id.name} - Flock {self.flock_id.name}'
        else:
            name = f'Gas: {self.product_id.name} - Growth {self.growth_tracking_id.name}'
        
        # Create landed cost
        landed_cost_vals = {
            'date': self.date,
            'target_model': 'picking',
            'picking_ids': [(4, picking.id)],
            'account_journal_id': self.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'cost_lines': [(0, 0, {
                'product_id': cost_product.id,
                'name': name,
                'split_method': 'by_quantity',
                'price_unit': self.quantity * self.product_id.standard_price,
            })],
        }
        
        landed_cost = self.env['stock.landed.cost'].create(landed_cost_vals)
        self.landed_cost_id = landed_cost.id
        
        # Compute and validate
        landed_cost.compute_landed_cost()
        if landed_cost.valuation_adjustment_lines and landed_cost.state == 'draft':
            landed_cost.button_validate()

    def _create_internal_consumption(self):
        """Create stock move to consume gas from inventory"""
        self.ensure_one()
        
        # Get flock info - from either flock_id or growth_tracking_id
        flock = self.flock_id or (self.growth_tracking_id.flock_id if self.growth_tracking_id else False)
        
        if not flock or not flock.location_id:
            return
        
        # Get the internal consumption operation type
        picking_type = self.env.ref('ibos_poultry.picking_type_internal_consumption', raise_if_not_found=False)
        
        if not picking_type:
            return
        
        # Get the virtual location for consumption (inventory loss)
        consumption_location = self.env['stock.location'].search([
            ('usage', '=', 'inventory'),
            ('is_loss_location', '=', True),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        raw_material_location = self.env['stock.location'].search([
            ('is_raw_material_location', '=', True),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not consumption_location:
            return
        
        # Create name based on context
        if self.flock_id:
            picking_name = f'Gas: {self.product_id.name} - {self.flock_id.name}'
        else:
            picking_name = f'Gas: {self.product_id.name} - {self.growth_tracking_id.name}'
        
        # Create picking first
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': raw_material_location.id,
            'location_dest_id': consumption_location.id,
            'origin': self.flock_id.name if self.flock_id else self.growth_tracking_id.name,
            'scheduled_date': self.date,
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock move within the picking
        move_vals = {
            'name': picking_name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'location_id': raw_material_location.id,
            'location_dest_id': consumption_location.id,
            'picking_id': picking.id,
            'picking_type_id': picking_type.id,
            'date': self.date,
            'origin': self.flock_id.name if self.flock_id else self.growth_tracking_id.name,
            'company_id': self.env.company.id,
        }
        
        stock_move = self.env['stock.move'].create(move_vals)
        self.stock_move_id = stock_move.id
        
        # Confirm and validate the picking
        picking.action_confirm()
        
        # Set quantity done
        for move_line in picking.move_ids:
            move_line.quantity = self.quantity
        
        # Validate the picking
        picking.button_validate()

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            if record.growth_tracking_id:
                name = f"{record.product_id.name} - {record.growth_tracking_id.name} ({record.date})"
            elif record.flock_id:
                name = f"{record.product_id.name} - {record.flock_id.name} ({record.date})"
            else:
                name = f"{record.product_id.name} ({record.date})"
            result.append((record.id, name))
        return result
    
    def action_process_record(self):
        """Process the record by creating landed costs and stock moves"""
        self.ensure_one()
        
        # Only process if not already processed
        if not self.landed_cost_id and not self.stock_move_id:
            self._create_landed_cost()
            self._create_internal_consumption()    
    def unlink(self):
        """Prevent deletion of processed records and records that would create date gaps"""
        for record in self:
            # Check if record is processed
            if record.landed_cost_id or record.stock_move_id:
                raise ValidationError(_(
                    'Cannot delete processed gas consumption record "%s". '
                    'This record has already been processed with landed cost and/or stock move. '
                ) % record.display_name)
            
            # Check if deletion would create a date gap
            if record.flock_id:
                # Get all other gas records for this flock
                other_records = self.env['poultry.gas.consumption'].search([
                    ('flock_id', '=', record.flock_id.id),
                    ('id', '!=', record.id)
                ], order='date')
                
                if other_records:
                    dates = other_records.mapped('date')
                    # Check if this record is between other dates (would create a gap)
                    dates_before = [d for d in dates if d < record.date]
                    dates_after = [d for d in dates if d > record.date]
                    
                    if dates_before and dates_after:
                        raise ValidationError(_(
                            'Cannot delete gas consumption record "%s". '
                            'Deleting this record would create a gap in the date sequence. '
                        ) % record.display_name)
            
            if record.growth_tracking_id:
                # Get all other gas records for this growth tracking
                other_records = self.env['poultry.gas.consumption'].search([
                    ('growth_tracking_id', '=', record.growth_tracking_id.id),
                    ('id', '!=', record.id)
                ], order='date')
                
                if other_records:
                    dates = other_records.mapped('date')
                    # Check if this record is between other dates (would create a gap)
                    dates_before = [d for d in dates if d < record.date]
                    dates_after = [d for d in dates if d > record.date]
                    
                    if dates_before and dates_after:
                        raise ValidationError(_(
                            'Cannot delete gas consumption record "%s". '
                            'Deleting this record would create a gap in the date sequence. '
                        ) % record.display_name)
        
        return super().unlink()