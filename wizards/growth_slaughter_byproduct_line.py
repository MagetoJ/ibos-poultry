from odoo import models, fields, api

class GrowthSlaughterByproductLine(models.TransientModel):
    _name = 'growth.slaughter.byproduct.line'
    _description = 'Growth Slaughter Byproduct Line'
    
    wizard_id = fields.Many2one(
        'growth.slaughter.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    byproduct_id = fields.Many2one(
        'mrp.bom.byproduct',
        string='BOM Byproduct',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Byproduct',
        related='byproduct_id.product_id',
        readonly=True
    )
    quantity = fields.Float(
        string='Quantity',
        digits=(10, 3),
        default=0.0,
        help='Quantity of this byproduct to produce'
    )
    percentage = fields.Float(
        string='Percentage of Bird(%)',
        compute='_compute_percentage',
        store=True,
        readonly=True,
        digits=(5, 2),
        help='Calculated percentage based on quantity and total dressed weight'
    )
    cost_share = fields.Float(
        string='Cost Share (%)',
        store=True,
        digits=(5, 2),
        help='Cost share percentage of this byproduct'
    )   
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='byproduct_id.product_uom_id',
        readonly=True
    )
    
    @api.depends('quantity', 'wizard_id.total_live_weight_kg')
    def _compute_percentage(self):
        """Calculate byproduct percentage based on quantity"""
        for line in self:
            if line.wizard_id and line.wizard_id.total_live_weight_kg and line.wizard_id.total_live_weight_kg > 0:
                line.percentage = (line.quantity / line.wizard_id.total_live_weight_kg) * 100.0
            else:
                line.percentage = 0.0
