# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    growth_tracking_id = fields.Many2one(
        'poultry.growth.tracking',
        string='Growth Tracking',
        help='Link to poultry growth tracking record',
        tracking=True,
        index=True
    )
    slaughter_id = fields.Many2one(
        'poultry.slaughter',
        string='Slaughter Record',
        help='Link to poultry slaughter record',
        tracking=True,
        index=True
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
        readonly=True,
        store=True
    )
    is_poultry_processing = fields.Boolean(
        string='Is Poultry Processing',
        compute='_compute_is_poultry_processing',
        store=True,
        help='True if this is a poultry processing manufacturing order'
    )
    live_bird_count = fields.Integer(
        string='Live Bird Count',
        help='Number of live birds being processed'
    )
    average_live_weight = fields.Float(
        string='Average Live Weight (g)',
        digits=(10, 2),
        help='Average weight per live bird'
    )
    total_live_weight = fields.Float(
        string='Total Live Weight (g)',
        compute='_compute_total_live_weight',
        store=True,
        digits=(10, 2),
        help='Total live weight (bird count × average weight)'
    )
    dressing_percentage = fields.Float(
        string='Dressing %',
        default=70.0,
        digits=(5, 2),
        help='Percentage yield from live to dressed weight'
    )
    
    # Smart button counts
    growth_tracking_count = fields.Integer(
        string='Growth Tracking',
        compute='_compute_smart_button_counts',
        help='Count of related growth tracking records'
    )
    slaughter_count = fields.Integer(
        string='Slaughter Records',
        compute='_compute_smart_button_counts',
        help='Count of related slaughter records'
    )
    
    @api.depends('growth_tracking_id', 'slaughter_id')
    def _compute_is_poultry_processing(self):
        """Determine if this is a poultry processing order"""
        for record in self:
            record.is_poultry_processing = bool(record.growth_tracking_id or record.slaughter_id)
    
    @api.depends('growth_tracking_id', 'slaughter_id')
    def _compute_smart_button_counts(self):
        """Compute counts for smart buttons"""
        for record in self:
            record.growth_tracking_count = 1 if record.growth_tracking_id else 0
            record.slaughter_count = 1 if record.slaughter_id else 0
    
    @api.depends('live_bird_count', 'average_live_weight')
    def _compute_total_live_weight(self):
        """Calculate total live weight"""
        for record in self:
            record.total_live_weight = record.live_bird_count * record.average_live_weight
    
    @api.onchange('growth_tracking_id')
    def _onchange_growth_tracking(self):
        """Auto-populate fields from growth tracking"""
        if self.growth_tracking_id:
            self.live_bird_count = self.growth_tracking_id.current_quantity
            self.average_live_weight = self.growth_tracking_id.current_weight or self.growth_tracking_id.average_weight
    
    @api.onchange('live_bird_count', 'total_live_weight', 'dressing_percentage')
    def _onchange_poultry_quantities(self):
        """Update product_qty based on poultry calculations"""
        if self.is_poultry_processing and self.total_live_weight and self.dressing_percentage:
            # Calculate expected dressed weight output
            dressed_weight = self.total_live_weight * (self.dressing_percentage / 100.0)
            self.product_qty = dressed_weight
    
    def button_mark_done(self):
        """Override to complete slaughter record when MO is done and handle context flags"""
        # Check if we should skip validation checks
        skip_checks = (
            self._context.get('skip_consumption') or 
            self._context.get('skip_overprocessed_check') or
            self._context.get('mo_overproduction')
        )
        
        if skip_checks:
            # Temporarily set quantities to avoid validation errors
            for move in self.move_raw_ids:
                # Calculate total done quantity from move lines
                total_qty_done = sum(move.move_line_ids.mapped('qty_done'))
                
                # Set expected quantity to match done quantity to avoid over-consumption warning
                if total_qty_done > move.product_uom_qty:
                    move.product_uom_qty = total_qty_done
        
        res = super().button_mark_done()
        
        # Apply cost_share to byproduct moves if provided in context
        byproduct_data = self._context.get('poultry_byproduct_data', [])
        if byproduct_data and self.move_byproduct_ids:
            for bp_data in byproduct_data:
                # Find the matching byproduct move
                byproduct_move = self.move_byproduct_ids.filtered(
                    lambda m: m.product_id.id == bp_data.get('product_id')
                )
                if byproduct_move:
                    # Update quantity and cost_share
                    byproduct_move.write({
                        'product_uom_qty': bp_data.get('quantity', byproduct_move.product_uom_qty),
                        'cost_share': bp_data.get('cost_share', 0.0),
                    })
        
        # Complete the linked slaughter record
        if self.slaughter_id and self.slaughter_id.state == 'scheduled':
            self.slaughter_id.action_complete()
        
        return res
    
    def action_view_growth_tracking(self):
        """Open the related growth tracking record"""
        self.ensure_one()
        if not self.growth_tracking_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Growth Tracking',
            'res_model': 'poultry.growth.tracking',
            'res_id': self.growth_tracking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_slaughter(self):
        """Open the related slaughter record"""
        self.ensure_one()
        if not self.slaughter_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Slaughter Record',
            'res_model': 'poultry.slaughter',
            'res_id': self.slaughter_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_confirm(self):
        """Override to apply byproduct cost_share from context after confirmation"""
        res = super().action_confirm()

        parms = self.env['ir.config_parameter'].sudo()
        for rec in self:
            if rec.product_id.tracking in ['serial', 'lot']:
                serial_id = self._generate_serial_lot(rec.product_id, rec.company_id, parms, rec.date_start or rec.date_planned_start)
                rec.lot_producing_id = serial_id
        
        
        # Apply cost_share to byproduct moves if provided in context
        byproduct_data = self._context.get('poultry_byproduct_data', [])
        if byproduct_data and self.move_byproduct_ids:
            for bp_data in byproduct_data:
                # Find the matching byproduct move
                byproduct_move = self.move_byproduct_ids.filtered(
                    lambda m: m.product_id.id == bp_data.get('product_id')
                )
                if byproduct_move:
                    # Update quantity and cost_share
                    byproduct_move.write({
                        'product_uom_qty': bp_data.get('quantity', byproduct_move.product_uom_qty),
                        'cost_share': bp_data.get('cost_share', 0.0),
                    })
    def generate_sns(self):
        """ Confirm the production order and generate serial/lot numbers.
         This method is called when the production order is confirmed.
         It checks the tracking type of the product and the serial_selection
         configuration parameter to determine the generation of serial/lot
         numbers. It generates the numbers based on the global configuration or
          product-specific configuration."""
        parms = self.env['ir.config_parameter'].sudo()
        for rec in self:
            if rec.product_id.tracking in ['serial', 'lot']:
                serial_id = self._generate_serial_lot(rec.product_id, rec.company_id, parms, rec.date_start or rec.date_planned_start)
                rec.lot_producing_id = serial_id
        
    def _generate_serial_lot(self, product, company, parms, mo_date=None):
        """Generate serial/lot number for a product.
        Args:
            product: product.product record
            company: res.company record
            parms: ir.config_parameter sudo object
            mo_date: Manufacturing order date (datetime)
        Returns:
            stock.lot record
        """
        # Format date prefix (YYYYMMDD format)
        date_prefix = ''
        if mo_date:
            date_prefix = mo_date.strftime('%Y%m%d') + '-'
        
        if parms.get_param('serial_no_from_mo.serial_selection') == 'global':
            digit = int(parms.get_param('serial_no_from_mo.digit'))
            prefix = parms.get_param('serial_no_from_mo.prefix') or ''
            # Combine date prefix with configured prefix
            full_prefix = date_prefix + prefix
            seq = self.env['ir.sequence'].sudo().search(
                [('code', '=', 'mrp.production.sequence')])
            if seq:
                seq.write({'prefix': prefix,
                           'padding': digit
                           })
            if not seq:
                self.env['ir.sequence'].create(
                    {'name': 'Mrp Production',
                     'implementation': 'standard',
                     'code': 'mrp.production.sequence',
                     'prefix': prefix, 'padding': digit})
            # Get the sequence number and prepend date
            seq_name = self.env['ir.sequence'].sudo().next_by_code('mrp.production.sequence')
            serial_id = self.env['stock.lot'].create(
                {'name': date_prefix + seq_name,
                    'product_id': product.id,
                    'company_id': company.id,
                })
        else:
            seq = self.env['ir.sequence'].sudo().search(
                [('code', '=', product.name)])
            prefix = product.product_tmpl_id.prefix or ''
            if seq:
                seq.write({
                    'prefix': prefix,
                    'padding': product.product_tmpl_id.digit,
                })
            if not seq:
                self.env['ir.sequence'].create({
                    'name': 'Mrp Production',
                    'implementation': 'standard',
                    'code': product.name,
                    'prefix': prefix,
                    'padding': product.product_tmpl_id.digit
                })
            # Get the sequence number and prepend date
            seq_name = self.env['ir.sequence'].sudo().next_by_code(product.name)
            serial_id = self.env['stock.lot'].create(
                {'name': date_prefix + seq_name,
                    'product_id': product.id,
                    'company_id': company.id,
                })
        return serial_id

    def _set_qty_producing(self):
        """Override to assign serial/lot numbers to byproduct move lines."""
        res = super()._set_qty_producing()
        parms = self.env['ir.config_parameter'].sudo()
        
        # Handle byproducts - assign serial/lot numbers to tracked byproducts
        byproduct_moves = self.move_finished_ids.filtered(
            lambda m: m.product_id != self.product_id and m.product_id.tracking in ['serial', 'lot']
        )
        
        for move in byproduct_moves:
            for move_line in move.move_line_ids:
                if not move_line.lot_id:
                    # Generate new serial for this byproduct
                    serial_id = self._generate_serial_lot(move.product_id, self.company_id, parms, self.date_start or self.date_planned_start)
                    move_line.lot_id = serial_id
        
        return res