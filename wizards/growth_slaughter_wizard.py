# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GrowthSlaughterWizard(models.TransientModel):
    _name = 'growth.slaughter.wizard'
    _description = 'Growth Tracking Processing Wizard'
    
    growth_tracking_id = fields.Many2one(
        'poultry.growth.tracking',
        string='Growth Tracking',
        required=True,
        readonly=True
    )
    flock_id = fields.Many2one(
        'poultry.flock',
        string='Flock',
        related='growth_tracking_id.flock_id',
        readonly=True
    )
    available_birds = fields.Integer(
        string='Available Birds',
        related='growth_tracking_id.current_quantity',
        readonly=True
    )
    quantity_to_process = fields.Integer(
        string='Quantity to Process',
        required=True,
        help='Number of live birds to process'
    )
    processing_date = fields.Date(
        string='Processing Date',
        required=True,
        default=fields.Date.today
    )
    average_weight = fields.Float(
        string='Average Live Weight (g)',
        digits=(10, 2),
        help='Average weight per bird'
    )
    total_live_weight = fields.Float(
        string='Total Live Weight (g)',
        compute='_compute_total_live_weight',
        digits=(10, 2),
        help='Total live weight of all birds to process'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Finished Product',
        required=True,
        domain="[('product_tmpl_id.bom_ids.is_main_bom', '=', True)]",
        help='Select the product to produce from processing'
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        required=True,
        domain="[('product_tmpl_id', '=', product_tmpl_id), ('is_main_bom', '=', True)]",
        help='Select the BoM for processing'
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        readonly=True
    )
    total_live_weight_kg = fields.Float(
        string='Total Live Weight (kg)',
        compute='_compute_total_live_weight',
        digits=(10, 3),
        help='Total live weight in kg (for byproduct calculations)'
    )
    byproduct_line_ids = fields.One2many(
        'growth.slaughter.byproduct.line',
        'wizard_id',
        string='Byproducts',
        help='Byproducts with percentage allocation'
    )
    has_byproducts = fields.Boolean(
        string='Has Byproducts',
        compute='_compute_has_byproducts',
        help='Indicates if the selected BOM has byproducts'
    )
    total_byproduct_quantity = fields.Float(
        string='Total Byproduct Qty (kg)',
        default=0.0,
        digits=(10, 3),
        help='Sum of all byproduct quantities'
    )
    total_byproduct_percentage = fields.Float(
        string='Total Byproduct %',
        compute='_compute_byproduct_percentages',
        digits=(5, 2),
        help='Sum of all byproduct percentages'
    )
    main_product_percentage = fields.Float(
        string='Main Product %',
        compute='_compute_byproduct_percentages',
        digits=(5, 2),
        help='Percentage remaining for main product (100% - byproduct %)'
    )
    main_product_quantity = fields.Float(
        string='Main Product Quantity',
        default=0.0,
        digits=(10, 3),
        help='Calculated main product quantity based on remaining percentage'
    )
    total_cost_share_percentage = fields.Float(
        string='Total Cost Share %',
        compute='_compute_total_cost_share',
        digits=(5, 2),
        help='Sum of all byproduct cost share percentages (must equal 100%)'
    )
    
    @api.depends('byproduct_line_ids.cost_share')
    def _compute_total_cost_share(self):
        """Calculate total cost share percentage"""
        for record in self:
            record.total_cost_share_percentage = sum(record.byproduct_line_ids.mapped('cost_share'))
    
    @api.depends('byproduct_line_ids')
    def _compute_has_byproducts(self):
        """Check if BOM has byproducts"""
        for record in self:
            record.has_byproducts = bool(record.byproduct_line_ids)
    
    @api.depends('quantity_to_process', 'average_weight')
    def _compute_total_live_weight(self):
        """Calculate total live weight"""
        for record in self:
            record.total_live_weight = record.quantity_to_process * record.average_weight
            record.total_live_weight_kg = record.total_live_weight / 1000.0
    
    @api.depends('byproduct_line_ids.quantity', 'byproduct_line_ids.percentage', 'total_live_weight_kg')
    def _compute_byproduct_percentages(self):
        """Calculate total byproduct percentage and main product quantity"""
        for record in self:
            total_byproduct_qty = sum(record.byproduct_line_ids.mapped('quantity'))
            total_byproduct_pct = sum(record.byproduct_line_ids.mapped('percentage'))
            
            record.total_byproduct_quantity = total_byproduct_qty
            record.total_byproduct_percentage = total_byproduct_pct
            record.main_product_percentage = 100.0 - total_byproduct_pct
            
    
    @api.onchange('growth_tracking_id')
    def _onchange_growth_tracking(self):
        """Set default values from growth tracking"""
        if self.growth_tracking_id:
            self.average_weight = self.growth_tracking_id.current_weight or self.growth_tracking_id.average_weight
            self.quantity_to_process = self.growth_tracking_id.current_quantity
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Auto-select BoM for the product"""
        if self.product_id:
            bom = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
                ('type', '=', 'normal'),
                ('is_main_bom', '=', True)
            ], limit=1)
            self.bom_id = bom if bom else False
        else:
            self.bom_id = False
    
    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        """Populate byproduct lines when BOM is selected"""
        if self.bom_id and self.bom_id.byproduct_ids:
            # Clear existing lines
            self.byproduct_line_ids = [(5, 0, 0)]
            
            # Create lines for each byproduct
            lines = []
            for byproduct in self.bom_id.byproduct_ids:
                lines.append((0, 0, {
                    'byproduct_id': byproduct.id,
                    'percentage': 0.0,  # User will set this
                }))
            self.byproduct_line_ids = lines
        else:
            self.byproduct_line_ids = [(5, 0, 0)]
    
    def _adjust_future_consumption(self, remaining_birds):
        """Adjust future feed and medicine consumption after partial slaughter.

        When only some birds are processed the remaining flock is smaller, so
        scheduled consumption quantities need to be scaled down proportionally.
        """
        self.ensure_one()

        growth = self.growth_tracking_id
        # current_quantity already reflects the birds still alive after this
        # slaughter (mortality/culling already deducted by the computed field).
        # remaining_birds = available_birds - quantity_to_process (passed in)
        previous_count = remaining_birds + self.quantity_to_process  # == available_birds
        if previous_count <= 0:
            return

        adjustment_ratio = remaining_birds / previous_count

        # Adjust future feed consumption records (on or after today)
        feed_records = self.env['poultry.growth.feed.consumption'].search([
            ('date', '>=', self.processing_date),
            ('growth_tracking_id', '=', growth.id),
        ])
        for feed in feed_records:
            feed.quantity = feed.quantity * adjustment_ratio

        # Adjust future medicine usage records (on or after today)
        medicine_records = self.env['poultry.growth.medicine.usage'].search([
            ('date', '>=', self.processing_date),
            ('growth_tracking_id', '=', growth.id),
        ])
        for medicine in medicine_records:
            medicine.quantity = medicine.quantity * adjustment_ratio

    def action_create_manufacturing_order(self):
        """Create manufacturing order for poultry processing"""
        self.ensure_one()
        
        if self.quantity_to_process <= 0:
            raise UserError(_('Quantity to process must be greater than zero.'))
        
        if self.quantity_to_process > self.available_birds:
            raise UserError(_(
                'Cannot process %d birds. Only %d birds available.'
            ) % (self.quantity_to_process, self.available_birds))
        
        if not self.bom_id:
            raise UserError(_('Please select a Bill of Materials for the product.'))
        
        if self.main_product_quantity <=0:
            raise UserError(_('Please set Main Product Quantity greater than zero.'))
        
        #check if bird quantity shown on form matches actual stock quants

        #check if number of different serial numbers in the location is exactly 1, otherwise block
        if self.growth_tracking_id and self.growth_tracking_id.poultry_location_id:
            poultry_loc = self.growth_tracking_id.poultry_location_id
            if not poultry_loc.stock_location_id:
                raise UserError(_("One of the required arguments does not exist. Please contact administrator"))
            internal_location_id = poultry_loc.stock_location_id.id
            lots_at_location = self.env['stock.lot'].search([
                ('location_id', '=', internal_location_id),
                ('product_id', '=', self.flock_id.product_id.id),
                ('product_qty', '>', 0),
            ])
            if len(lots_at_location) > 1:
                raise UserError(_(
                    "There exists more than one bird batch at %s: Bird moves are not meant "
                    "to be done manually via Inventory adjustment and will result in "
                    "Manufacturing Errors. Please ensure there is only one active serial "
                    "number in a location at any given time."
                ) % (poultry_loc.display_name,))
        

        diff = self.available_birds - self.quantity_to_process
        # Validate byproduct percentages if present
        # if self.byproduct_line_ids:
        #     # Validate cost share totals to 100%
        #     # if abs(self.total_cost_share_percentage - 100.0) > 0.01:
        #     #     raise UserError(_(
        #     #         'Total Cost Share must equal 100%%. '
        #     #         'Current total: %.2f%%. '
        #     #         'Please adjust cost share percentages so they sum to exactly 100%%.'
        #     #     ) % self.total_cost_share_percentage)
            
        #     # Ensure byproducts + main product = 100%
        #     # if self.total_byproduct_percentage > 100.0:
        #     #     raise UserError(_(
        #     #         'Total byproduct percentage (%.2f%%) exceeds 100%%. '
        #     #         'Please reduce byproduct quantities.'
        #     #     ) % self.total_byproduct_percentage)
            
        #     if self.main_product_quantity <= 0:
        #         raise UserError(_(
        #             'Main product quantity cannot be zero or negative. '
        #             'Current byproduct total: %.2f%%. Main product: %.2f%%. '
        #             'Please reduce byproduct quantities to leave some for the main product.'
        #         ) % (self.total_byproduct_percentage, self.main_product_percentage))
        
        # Get poultry source location
        poultry_location = self.growth_tracking_id.poultry_location_id
        location_src_id = poultry_location.stock_location_id.id if poultry_location and poultry_location.stock_location_id else False
        quants_at_location = self.env['stock.quant'].search([
            ('product_id', '=', self.flock_id.product_id.id),
            ('location_id', '=', location_src_id),
            ('quantity', '>', 0)
        ])
        if self.available_birds != sum(quants_at_location.mapped('quantity')):
            raise UserError(_(
                'An error occurred while validating available bird quantity. '
                'You tried processing %d birds, but actual stock quantity at location is %d.'
            ) % (self.available_birds, sum(quants_at_location.mapped('quantity'))))

        # Calculate main product quantity (total live weight minus byproducts)
        main_qty = self.main_product_quantity if self.byproduct_line_ids else self.total_live_weight_kg
        
        # Prepare byproduct data to pass to MO
        byproduct_data = []
        if self.byproduct_line_ids:
            for line in self.byproduct_line_ids:
                if line.quantity > 0:
                    byproduct_data.append({
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'cost_share': line.cost_share,
                    })
        
        # Create manufacturing order with context for byproduct quantities
        mo_vals = {
            'product_id': self.product_id.id,
            'product_qty': main_qty,
            'product_uom_id': self.product_id.uom_id.id,
            'bom_id': self.bom_id.id,
            'date_start': fields.Datetime.now(),
            'growth_tracking_id': self.growth_tracking_id.id,
            'live_bird_count': self.quantity_to_process,
            'average_live_weight': self.average_weight,
            'origin': f'{self.growth_tracking_id.name} / {self.flock_id.name}',
        }
        
        # Set source location if poultry location has a stock location
        if location_src_id:
            mo_vals['location_src_id'] = location_src_id
        
        # Create MO with context containing byproduct data
        mo = self.env['mrp.production'].with_context(
            poultry_byproduct_data=byproduct_data,
            poultry_main_product_percentage=self.main_product_percentage if self.byproduct_line_ids else 100.0
        ).create(mo_vals)
        
        # Create slaughter record for tracking
        slaughter_vals = {
            'growth_tracking_id': self.growth_tracking_id.id,
            'slaughter_date': self.processing_date,
            'quantity_to_slaughter': self.quantity_to_process,
            'average_weight': self.average_weight,
            'state': 'scheduled',
        }
        slaughter = self.env['poultry.slaughter'].create(slaughter_vals)
        
        # Link the MO to the slaughter record
        mo.slaughter_id = slaughter.id
        
        # Confirm the MO automatically to bypass quantity difference warning
        mo.action_confirm()
        
        # Generate serial/lot numbers for tracked products
        mo.generate_sns()
        
        # After confirmation, update live bird component quantity and set lot
        if mo.move_raw_ids:
            live_bird_move = mo.move_raw_ids.filtered(
                lambda m: m.product_id.poultry_product_type == 'chick' or 
                         m.product_id == self.flock_id.product_id
            )
            if live_bird_move:
                # Update the move quantity directly using SQL to avoid triggering computations
                self.env.cr.execute(
                    "UPDATE stock_move SET product_uom_qty = %s WHERE id = %s",
                    (self.quantity_to_process, live_bird_move.id)
                )
                live_bird_move.invalidate_recordset(['product_uom_qty'])
                
                # Set lot on move lines if available
                if self.flock_id.lot_id and live_bird_move.move_line_ids:
                    live_bird_move.move_line_ids.write({
                        'lot_id': self.flock_id.lot_id.id,
                    })
        
        # After confirmation, ensure byproduct moves have updated quantities and proper move lines
        if self.byproduct_line_ids and mo.move_byproduct_ids:
            for line in self.byproduct_line_ids:
                if line.quantity > 0:
                    # Find matching byproduct move
                    byproduct_move = mo.move_byproduct_ids.filtered(
                        lambda m: m.product_id == line.product_id
                    )
                    if byproduct_move:
                        # Update quantity if not already done by action_confirm
                        byproduct_move.product_uom_qty = line.quantity
                        # Force action to ensure move lines are created/updated
                        byproduct_move._action_confirm()
        
        # Set quantities done to match expected quantities to avoid consumption warning
        # Set quantity producing
        mo.qty_producing = mo.product_qty
        
        # Ensure lot is assigned to finished product move lines
        if mo.lot_producing_id and mo.move_finished_ids:
            main_product_move = mo.move_finished_ids.filtered(
                lambda m: m.product_id == mo.product_id
            )
            if main_product_move and main_product_move.move_line_ids:
                main_product_move.move_line_ids.write({
                    'lot_id': mo.lot_producing_id.id,
                })
        
        # Set done quantities on raw material move lines
        for move in mo.move_raw_ids:
            if move.state not in ['done', 'cancel']:
                # Check if this is the live bird component
                is_live_bird = (move.product_id.poultry_product_type == 'chick' or 
                               move.product_id == self.flock_id.product_id)
                qty_to_set = self.quantity_to_process if is_live_bird else move.product_uom_qty
                
                # Set quantity on move lines (detailed operations)
                for move_line in move.move_line_ids:
                    move_line.qty_done = qty_to_set
        
        # Set done quantities on byproduct move lines
        for move in mo.move_byproduct_ids:
            if move.state not in ['done', 'cancel']:
                for move_line in move.move_line_ids:
                    move_line.qty_done = move.product_uom_qty
                    # Generate lot for tracked byproducts if not already assigned
                    if move.product_id.tracking in ['serial', 'lot'] and not move_line.lot_id:
                        parms = self.env['ir.config_parameter'].sudo()
                        serial_id = mo._generate_serial_lot(
                            move.product_id, 
                            mo.company_id, 
                            parms, 
                            mo.date_start or mo.date_planned_start
                        )
                        move_line.lot_id = serial_id.id
        
        # Mark as done with context to skip consumption warning
        # Use multiple context flags to handle lot-tracked products
        mo.with_context(
            skip_consumption=True,
            skip_backorder=True,
            skip_overprocessed_check=True,
            mo_overproduction=True,
            no_produce_line_check=True
        ).button_mark_done()
        
        # Set growth tracking state to partially processed when first MO is created
       
        if diff:
            self.growth_tracking_id.state = 'partially_processed'
            # Adjust future consumption records proportionally for remaining birds
            self._adjust_future_consumption(diff)
        else:
            self.env['poultry.growth.tracking'].browse(self.growth_tracking_id.id).total_slaughtered = self.quantity_to_process
            self.env['poultry.growth.tracking'].browse(self.growth_tracking_id.id).action_complete_slaughter()
            self.growth_tracking_id.state = 'slaughtered'
        
        # Return action to view the created manufacturing order
        return {
            'type': 'ir.actions.act_window',
            'name': 'Processing Order',
            'res_model': 'mrp.production',
            'res_id': mo.id,
            'view_mode': 'form',
            'target': 'current',
        }

