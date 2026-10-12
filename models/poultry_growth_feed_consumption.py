from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class PoultryGrowthFeedConsumption(models.Model):
    _name = 'poultry.growth.feed.consumption'
    _description = 'Poultry Growth Phase Feed Consumption'
    _rec_name = 'product_id'
    _order = 'date desc, id desc'
    _sql_constraints = [
        ('unique_growth_date', 'UNIQUE(growth_tracking_id, date, product_id)', 
         'Only one feed consumption entry per product per day is allowed for each growth tracking!'),
    ]

    growth_tracking_id = fields.Many2one(
        'poultry.growth.tracking',
        string='Growth Tracking',
        required=True,
        ondelete='cascade',
        index=True,
        help='Link to growth tracking record'
    )
    age_from = fields.Integer(
        string='Age',   
        help='Age of chicks for this feed consumption record'
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
        index=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Feed Product',
        required=True,
        domain=[('poultry_product_type', '=', 'feed')]
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        digits='Product Unit of Measure'
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
        """Create landed cost to allocate feed cost"""
        self.ensure_one()
        
        # Get growth tracking and flock info
        growth = self.growth_tracking_id
        flock = growth.flock_id
        
        if not flock or not flock.product_id or not flock.location_id:
            return
        
        # Get the original receipt picking from the flock
        receipt_picking = self.env['stock.picking'].search([
            ('purchase_id', '=', flock.purchase_order_id.id),
            ('state', '=', 'done')
        ], limit=1)
        
        if not receipt_picking:
            return
        
        # Create unique name with timestamp
        name = f'Feed: {self.product_id.name} - Growth {growth.name} - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        
        # Create stock move for feed consumption
        stock_move = self._create_stock_move()
        
        if not stock_move:
            return
        
        default_poultry_lc_journal = self.env['account.journal'].search([('is_poultry_processing_journal', '=', True)], limit=1)
        if not default_poultry_lc_journal:
            raise ValidationError(_('No poultry processing journal found. Please create a journal with "Is Poultry Processing Journal" enabled.'))
        
        # Create landed cost
        landed_cost_vals = {
            'date': self.date,
            'picking_ids': [(6, 0, [receipt_picking.id])],
            'account_journal_id': default_poultry_lc_journal.id,
            'cost_lines': [(0, 0, {
                'product_id': self.product_id.id,
                'name': f'Feed Cost: {self.product_id.name}',
                'account_id': default_poultry_lc_journal.default_account_id.id,
                'price_unit': self.quantity * self.product_id.standard_price,
                'split_method': 'by_quantity',
            })],
        }
        
        landed_cost = self.env['stock.landed.cost'].create(landed_cost_vals)
        
        # Compute the landed cost to generate valuation adjustment lines automatically
        landed_cost.compute_landed_cost()
        
        # Link the landed cost and stock move to this record
        self.write({
            'landed_cost_id': landed_cost.id,
            'stock_move_id': stock_move.id,
        })
        
        # Validate the landed cost
        if landed_cost.state == 'draft':
            landed_cost.button_validate()

    def _create_stock_move(self):
        """Create stock move for feed consumption"""
        self.ensure_one()
        
        growth = self.growth_tracking_id
        flock = growth.flock_id
        
        if not flock or not flock.location_id:
            return False
        
        # Get loss location
        loss_location = self.env['stock.location'].search([
            ('is_loss_location', '=', True),
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)
        
        if not loss_location:
            return False
        
        # Get raw material location
        raw_material_location = self.env['stock.location'].search([
            ('is_raw_material_location', '=', True),
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)
        
        if not raw_material_location:
            return False
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', '=', raw_material_location.id),
            ('quantity', '>=', self.quantity)
        ])
        if not quants:
            raise ValidationError(_('Not enough stock of %s in raw material location to consume. Please replenish inventory before processing feed consumption.') % self.product_id.display_name)
        else:
            picking_name = f'Feed: {self.product_id.name} - Growth {growth.name}'
            
            # Create stock move
            move_vals = {
                'name': picking_name,
                'product_id': self.product_id.id,
                'product_uom_qty': self.quantity,
                'product_uom': self.product_id.uom_id.id,
                'location_id': raw_material_location.id,
                'location_dest_id': loss_location.id,
                'date': self.date,
                'origin': growth.name,
            }
            
            move = self.env['stock.move'].create(move_vals)
            
            # Confirm and process the move
            if move.state == 'draft':
                move._action_confirm()
                move._action_assign()
                move._set_quantity_done(self.quantity)
                move._action_done()
            
            return move
    def _create_internal_consumption(self):
        """Create stock move to consume feed from inventory"""
        self.ensure_one()
        
        # Get flock info - from either flock_id or growth_tracking_id
        flock = self.growth_tracking_id.flock_id if self.growth_tracking_id else False
        
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
        if self.growth_tracking_id.flock_id:
            picking_name = f'Feed: {self.product_id.name} - {self.growth_tracking_id.flock_id.name}'
        else:
            picking_name = f'Feed: {self.product_id.name} - {self.growth_tracking_id.name}'
        
        # Create picking first
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': raw_material_location.id,
            'location_dest_id': consumption_location.id,
            'origin': self.growth_tracking_id.flock_id.name if self.growth_tracking_id.flock_id else self.growth_tracking_id.name,
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
            'origin': self.growth_tracking_id.flock_id.name if self.growth_tracking_id.flock_id else self.growth_tracking_id.name,
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

    def action_process_record(self):
        """Process the feed consumption record (create landed cost and stock move)"""
        for record in self:
            raw_material_location = self.env['stock.location'].search([
            ('is_raw_material_location', '=', True),
            ('company_id', '=', self.env.company.id)
            ], limit=1)
            quants = self.env['stock.quant'].search([
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', raw_material_location.id),
                ('quantity', '>=', self.quantity)
            ])
            if not quants:
                raise ValidationError(_('Not enough stock of %s in raw material location to consume. Please replenish inventory before processing feed consumption.') % self.product_id.display_name)
            else:
                if not record.landed_cost_id and not record.stock_move_id:
                    record._create_landed_cost()
                    record._create_internal_consumption()

    def name_get(self):
        """Custom name display"""
        result = []
        for record in self:
            if record.growth_tracking_id:
                name = f"{record.product_id.name} - Growth {record.growth_tracking_id.name} ({record.date})"
            else:
                name = f"{record.product_id.name} ({record.date})"
            result.append((record.id, name))
        return result
