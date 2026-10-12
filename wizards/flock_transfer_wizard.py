# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FlockTransferWizard(models.TransientModel):
    _name = 'flock.transfer.wizard'
    _description = 'Flock Transfer Wizard'
    
    flock_id = fields.Many2one(
        'poultry.flock',
        string='Flock',
        required=True,
        readonly=True,
        help='The flock to transfer'
    )
    batch_number = fields.Char(
        string='Batch Number',
        related='flock_id.name',
        readonly=True
    )
    current_quantity = fields.Integer(
        string='Current Quantity',
        related='flock_id.current_quantity',
        readonly=True
    )
    current_weight = fields.Float(
        string='Current Average Weight',
        related='flock_id.current_weight',
        readonly=True
    )
    poultry_location_id = fields.Many2one(
        'poultry.location',
        string='Destination Poultry Location',
        required=True,
        help='Select the poultry location where the flock will be transferred'
    )
    stock_location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        related='poultry_location_id.stock_location_id',
        readonly=True
    )
    transfer_date = fields.Datetime(
        string='Transfer Date',
        default=fields.Datetime.now,
        required=True
    )
    notes = fields.Text(
        string='Notes'
    )
    
    def action_confirm_transfer(self):
        """Create internal transfer and update flock"""
        self.ensure_one()
        
        if not self.poultry_location_id:
            raise UserError(_('Please select a destination poultry location.'))
        
        if not self.poultry_location_id.stock_location_id:
            raise UserError(_('The selected poultry location does not have an associated stock location.'))
        
        if self.flock_id.current_quantity <= 0:
            raise UserError(_('Cannot transfer a flock with no birds.'))
        
        # # Check if location is already occupied
        # existing_flock = self.env['poultry.flock'].search([
        #     ('poultry_location_id', '=', self.poultry_location_id.id),
        #     ('state', '=', 'transfer'),
        #     ('id', '!=', self.flock_id.id)
        # ], limit=1)
        
        # if existing_flock:
        #     raise UserError(_(
        #         'Location "%s" is already occupied by flock %s. '
        #         'Please select a different location or clear the existing flock first.'
        #     ) % (self.poultry_location_id.name, existing_flock.name))
        
        # Check if location has active growth tracking
        existing_growth = self.env['poultry.growth.tracking'].search([
            ('poultry_location_id', '=', self.poultry_location_id.id),
            ('state', 'in', ['draft', 'confirmed','partially_processed']),
            ('active', '=', True)
        ], limit=1)
        
        if existing_growth:
            raise UserError(_(
                'Location "%s" already has active growth tracking (%s). '
                'Please complete or archive the existing tracking before transferring a new flock.'
            ) % (self.poultry_location_id.name, existing_growth.flock_id.name))
        
        # Check if location has sufficient capacity
        if self.poultry_location_id.capacity > 0:  # Only check if capacity is set
            if self.flock_id.current_quantity > self.poultry_location_id.capacity:
                raise UserError(_(
                    'Location "%s" has a capacity of %d birds, '
                    'but you are trying to transfer %d birds. '
                    'Please select a location with sufficient capacity.'
                ) % (
                    self.poultry_location_id.name,
                    self.poultry_location_id.capacity,
                    self.flock_id.current_quantity
                ))
        
        # Create internal transfer
        picking = self._create_internal_transfer()
        
        # Update flock
        self.flock_id.write({
            'poultry_location_id': self.poultry_location_id.id,
            'location_id': self.poultry_location_id.stock_location_id.id,
            'state': 'transfer'
        })
        
        # Create initial growth tracking record
        growth_tracking = self._create_growth_tracking()
        
        # Return action to view the created growth tracking record
        return {
            'type': 'ir.actions.act_window',
            'name': _('Growth Tracking'),
            'res_model': 'poultry.growth.tracking',
            'res_id': growth_tracking.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _create_internal_transfer(self):
        """Create an internal transfer for the flock"""
        self.ensure_one()
        
        # Get picking type for internal transfers
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '!=', False)
        ], limit=1)
        
        if not picking_type:
            raise UserError(_('No internal transfer picking type found. Please configure your warehouse.'))
        
        # Prepare picking values
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.flock_id.location_id.id,
            'location_dest_id': self.poultry_location_id.stock_location_id.id,
            'scheduled_date': self.transfer_date,
            'origin': self.flock_id.name,
            'note': self.notes or f'Transfer of flock {self.flock_id.name} to {self.poultry_location_id.name}',
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create stock move for the birds
        move_vals = {
            'name': f'Transfer {self.flock_id.name}',
            'picking_id': picking.id,
            'product_id': self.flock_id.product_id.id,
            'product_uom_qty': self.flock_id.current_quantity,
            'product_uom': self.flock_id.product_id.uom_id.id,
            'location_id': self.flock_id.location_id.id,
            'location_dest_id': self.poultry_location_id.stock_location_id.id,
            'origin': self.flock_id.name,
        }
        
        move = self.env['stock.move'].create(move_vals)
        
        # Confirm the picking to make it ready
        picking.action_confirm()
        
        # CRITICAL: action_confirm() auto-creates move lines, which may pick wrong lots
        # Delete any auto-created move lines before we create the correct one
        auto_created_lines = picking.move_line_ids
        if auto_created_lines:
            auto_created_lines.unlink()
        
        # Create move lines manually with the specific lot_id to ensure correct lot is picked
        # This prevents Odoo from auto-assigning the wrong lot when multiple batches exist in same location
        move_line_vals = {
            'move_id': move.id,
            'picking_id': picking.id,
            'product_id': self.flock_id.product_id.id,
            'product_uom_id': self.flock_id.product_id.uom_id.id,
            'location_id': self.flock_id.location_id.id,
            'location_dest_id': self.poultry_location_id.stock_location_id.id,
            'quantity': self.flock_id.current_quantity,
            'lot_id': self.flock_id.lot_id.id if self.flock_id.lot_id else False,
        }
        
        move_line = self.env['stock.move.line'].create(move_line_vals)
        
        # Mark move as assigned since we created the move line manually
        move.state = 'assigned'
        
        # Validate with immediate transfer wizard to handle the transfer properly
        res = picking.button_validate()
        
        # If a wizard appears (for backorder or immediate transfer), auto-process it
        if isinstance(res, dict) and res.get('res_model'):
            if res.get('res_model') == 'stock.immediate.transfer':
                immediate_transfer = self.env['stock.immediate.transfer'].browse(res.get('res_id'))
                immediate_transfer.process()
            elif res.get('res_model') == 'stock.backorder.confirmation':
                backorder = self.env['stock.backorder.confirmation'].browse(res.get('res_id'))
                backorder.process()
        
        return picking
    
    def _create_growth_tracking(self):
        """Create initial growth tracking record for the transferred flock"""
        self.ensure_one()
        
        # Use flock's current weight (from latest weighing or initial weight if no weighing records)
        average_weight = self.flock_id.current_weight if self.flock_id.current_weight > 0 else 0.0
        sample_size = self.flock_id.sample_size if self.flock_id.sample_size > 0 else 10
        
        # Get flock's initial age from bird_age field
        # bird_age='21' means 21-day-old birds -> start growth tracking at age 20 (last completed age in 0-indexed schedule)
        # bird_age='0' means day-old chicks -> start at age 0
        bird_age_int = int(self.flock_id.bird_age) if self.flock_id.bird_age else 0
        initial_age = bird_age_int - 1 if bird_age_int > 0 else 0
        
        # Calculate initial flock cost based on current birds (cost per bird * current quantity)
        # This accounts for mortality during brooding phase - dead birds don't carry cost forward
        initial_flock_cost = self.flock_id.current_cost_per_bird * self.flock_id.current_quantity
        
        # Calculate brooding_days inline to avoid stale computed field values
        brooding_days = 0
        if self.flock_id.arrival_date and self.flock_id.estimated_end_of_brooding:
            delta = self.flock_id.estimated_end_of_brooding - self.flock_id.arrival_date
            brooding_days = max(0, delta.days)
        
        # Create growth tracking record with brooding_days, estimated_slaughter_date, and feed_schedule_id
        growth_tracking_vals = {
            'flock_id': self.flock_id.id,
            'tracking_date': self.transfer_date.date() if self.transfer_date else fields.Date.today(),
            'initial_quantity': self.flock_id.current_quantity,
            'initial_age_days': initial_age,
            'brooding_days': brooding_days,  # Use calculated value instead of potentially stale computed field
            'estimated_slaughter_date': self.flock_id.estimated_slaughter_date,  # Propagate slaughter date
            'feed_schedule_id': self.flock_id.feed_schedule_id.id if self.flock_id.feed_schedule_id else False,  # Propagate feed schedule
            'vaccine_schedule_id': self.flock_id.vaccine_schedule_id.id if self.flock_id.vaccine_schedule_id else False,  # Propagate vaccine schedule
            'mortality_schedule_id': self.flock_id.mortality_schedule_id.id if self.flock_id.mortality_schedule_id else False,  # Propagate mortality schedule
            'weight_schedule_id': self.flock_id.weight_schedule_id.id if self.flock_id.weight_schedule_id else False,  # Propagate weight schedule
            'initial_flock_cost': initial_flock_cost,  # Cost per bird * current quantity
            'notes': f'Initial growth tracking record created from transfer to {self.poultry_location_id.name}. '
                     f'Starting with {self.flock_id.current_quantity} birds at age {initial_age} days. '
                     f'Current weight: {average_weight} kg (based on {sample_size} bird sample)' if average_weight > 0 
                     else f'Initial growth tracking record created from transfer to {self.poultry_location_id.name}. '
                          f'Starting with {self.flock_id.current_quantity} birds at age {initial_age} days.',
        }
        
        growth_tracking = self.env['poultry.growth.tracking'].create(growth_tracking_vals)
        
        # Create initial weighing record to set current_weight (computed from weighing records)
        if average_weight > 0:
            self.env['poultry.weighing'].create({
                'growth_tracking_id': growth_tracking.id,
                'weighing_date': fields.Date.today(),
                'age_from': initial_age,
                'sample_size': sample_size,
                'average_weight': average_weight,
                'notes': f'Initial weight from flock transfer to {self.poultry_location_id.name}'
            })
        
        return growth_tracking
