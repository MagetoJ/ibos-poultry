# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_poultry_receipt = fields.Boolean(
        string='Is Poultry Receipt',
        compute='_compute_is_poultry_receipt',
        store=True,
        help='Indicates if this receipt contains poultry products'
    )
    is_backdated_receipt = fields.Boolean(
        string='Is Backdated Receipt',
        compute='_compute_is_poultry_receipt',
        store=True,
        help='Indicates if this receipt is backdated (date_done before today)'
    )

    flock_ids = fields.One2many(
        'poultry.flock',
        'picking_id',
        string='Flocks',
        help='Flocks created from this receipt'
    )

    flock_count = fields.Integer(
        string='Flock Count',
        compute='_compute_flock_count',
        store=True,
        help='Number of flocks created from this receipt'
    )

    @api.depends('purchase_id.is_poultry_purchase', 'move_line_ids.product_id.poultry_product_type')
    def _compute_is_poultry_receipt(self):
        """Check if receipt is for poultry purchase"""
        for picking in self:
            # First check if linked to a poultry purchase order
            if picking.purchase_id and picking.purchase_id.is_poultry_purchase:
                picking.is_poultry_receipt = True
            else:
                # Otherwise check if this specific picking has chick move lines
                has_chick_moves = any(
                    ml.product_id.poultry_product_type == 'chick'
                    for ml in picking.move_ids
                )
                picking.is_poultry_receipt = has_chick_moves
                picking.is_backdated_receipt = has_chick_moves

    def button_validate(self):
        """Override to create flock when chicks are received"""
        res = super().button_validate()
        
        for picking in self:
            if picking.is_poultry_receipt and picking.state == 'done' and not picking.is_backdated_receipt:
                # Check if flocks already exist for this picking
                existing_flocks = self.env['poultry.flock'].search([('picking_id', '=', picking.id)])
                if not existing_flocks:
                    picking._create_flock_from_receipt()
        
        return res
    
    @api.depends('flock_ids')
    def _compute_flock_count(self):
        """Compute number of flocks created from this receipt"""
        for picking in self:
            picking.flock_count = len(picking.flock_ids)

    def _create_flock_from_receipt(self):
        """Create a flock record when chicks are received"""
        self.ensure_one()

        #ensure it is a receipt and not a return
        if self.picking_type_code != 'incoming':
            return
        
        else:
            
            # Find chick product move lines
            chick_move_lines = self.move_line_ids.filtered(
                lambda ml: ml.product_id.poultry_product_type == 'chick' and ml.state == 'done' and ml.qty_done > 0
            )

            if len(chick_move_lines) > 1:
                raise UserError(_('Multiple chick move lines found. Please ensure only one flock is processed per receipt.'))
            
            if not chick_move_lines:
                return
            
            # Create a flock for each move line (each serial/lot)
            for move_line in chick_move_lines:
                # Get receipt location from PO or use destination location
                receipt_location = self.purchase_id.poultry_receipt_location_id if self.purchase_id.poultry_receipt_location_id else move_line.location_dest_id
                
                # Poultry costs are always untaxed: Odoo's standard purchase
                # screens keep their normal tax behaviour, but the flock cost
                # must not include recoverable tax. Weighted average over all
                # PO lines of this product.
                purchase_lines = self.purchase_id.order_line.filtered(
                    lambda l: l.product_id == move_line.product_id and not l.display_type
                )
                initial_cost = 0.0
                total_qty = 0.0
                total_cost = 0.0
                for pl in purchase_lines:
                    qty = pl.product_uom._compute_quantity(pl.product_qty, pl.product_id.uom_id)
                    total_qty += qty
                    total_cost += qty * pl._get_stock_move_price_unit()  # untaxed, per stock UoM
                if total_qty:
                    initial_cost = total_cost / total_qty
                
                # Create flock
                flock_vals = {
                    'purchase_order_id': self.purchase_id.id,
                    'picking_id': self.id,
                    'product_id': move_line.product_id.id,
                    'lot_id': move_line.lot_id.id if move_line.lot_id else False,
                    'date_received': self.scheduled_date or self.date_done or fields.Datetime.now(),
                    'initial_quantity': int(move_line.qty_done),
                    'location_id': receipt_location.id,
                    'initial_weight': 50.0,
                    'target_weight': 200.0,
                    'initial_cost_per_bird': initial_cost,
                    'state': 'received',
                }
                
                flock = self.env['poultry.flock'].create(flock_vals)
                
                # Post message
                message = _('Flock %s created with %d birds (Lot: %s) from PO %s') % (
                    flock.name, 
                    flock.initial_quantity,
                    move_line.lot_id.name if move_line.lot_id else 'N/A',
                    self.purchase_id.name
                )
                self.message_post(body=message)
                flock.message_post(body=_('Flock created from receipt %s') % self.name)
    
    def create_backdated_flock_from_receipt(self):
        """Create a flock record when chicks are received"""
        self.ensure_one()

        #ensure it is a receipt and not a return
        if self.picking_type_code != 'incoming':
            return
        
        else:
            
            # Find chick product move lines
            chick_move_lines = self.move_line_ids.filtered(
                lambda ml: ml.product_id.poultry_product_type == 'chick' and ml.state == 'done' and ml.qty_done > 0
            )

            if len(chick_move_lines) > 1:
                raise UserError(_('Method not allowed. Create two separate backdated receipts with required quantity.'))
            
            if not chick_move_lines:
                return
            
            # Create a flock for each move line (each serial/lot)
            for move_line in chick_move_lines:
                # Get receipt location from PO or use destination location
                receipt_location = self.purchase_id.poultry_receipt_location_id if self.purchase_id.poultry_receipt_location_id else move_line.location_dest_id
                
                cost_per_bird = move_line.product_id.standard_price or 0.0
                
                # Create flock
                flock_vals = {
                    'purchase_order_id': self.purchase_id.id,
                    'picking_id': self.id,
                    'product_id': move_line.product_id.id,
                    'lot_id': move_line.lot_id.id if move_line.lot_id else False,
                    'date_received': self.scheduled_date or self.date_done or fields.Datetime.now(),
                    'initial_quantity': int(move_line.qty_done),
                    'location_id': receipt_location.id,
                    'initial_weight': 50.0,
                    'target_weight': 200.0,
                    'initial_cost_per_bird': cost_per_bird,
                    'state': 'received',
                }
                
                flock = self.env['poultry.flock'].create(flock_vals)
                
                # Post message
                message = _('Backdated Flock %s created with %d birds (Lot: %s) from PO %s') % (
                    flock.name, 
                    flock.initial_quantity,
                    move_line.lot_id.name if move_line.lot_id else 'N/A',
                    self.purchase_id.name
                )
                self.message_post(body=message)
                flock.message_post(body=_('Backdated Flock created from receipt %s') % self.name)
