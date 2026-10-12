# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class VaccinationSchedule(models.Model):
    _name = 'vaccination.schedule'
    _description = 'Vaccination Schedule Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    
    name = fields.Char(
        string='Schedule Name',
        required=True,
        help='Name of the vaccination schedule (e.g., Broiler Vaccination Program)'
    )
    bird_type = fields.Selection([
        ('broiler', 'Broiler'),
        ('layer', 'Layer'),
        ('breeder', 'Breeder'),
        ('other', 'Other')
    ], string='Bird Type',
       required=True,
       default='broiler',
       help='Type of bird this vaccination schedule is designed for'
    )
    line_ids = fields.One2many(
        'vaccination.schedule.line',
        'schedule_id',
        string='Schedule Lines',
        help='Vaccination schedule line items'
    )
    notes = fields.Text(
        string='Notes',
        help='General notes about this vaccination schedule'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    #compute partially consumed vaccine batches
    partially_consumed_batch_ids = fields.Many2many(
        string="Partially Consumed Batches",
        comodel_name='stock.lot',
        help='Vaccine batches that have been partially consumed',
        compute='_compute_partially_consumed_batches'
    )

    def scrap_partially_consumed_batches(self):
        """
        Scrap the partially consumed vaccine batches and log the action
        """
        for record in self:
            if record.partially_consumed_batch_ids:
                for batch in record.partially_consumed_batch_ids:
                                  
                    batch_location = self.env['stock.location'].search([('is_raw_material_location', '=', True)], limit=1)
                    origin = f"Scrap from Vaccination Schedule: {record.name}"
                    scrap = self.env['stock.scrap'].create({
                        'product_id': batch.product_id.id,
                        'product_uom_id': batch.product_id.uom_id.id,
                        'location_id': batch_location.id,
                        'lot_id': batch.id,
                        'scrap_qty': batch.product_qty,
                        'date_done': fields.Datetime.now(),
                        'origin': origin,
                    })
                    scrap.action_validate()
                record.message_post(body=_("Partially consumed vaccine batches have been scrapped."))
            else:
                record.message_post(body=_("No partially consumed vaccine batches to scrap."))
    
    def _compute_partially_consumed_batches(self):
        """
        Compute vaccine batches where current on-hand quantity is less than 
        the original quantity from the purchase order
        """
        for record in self:
            partially_consumed_batches = self.env['stock.lot']
            
            # Get all lots for vaccine/medicine products
            lots = self.env['stock.lot'].search([
                ('product_id.poultry_product_type', '=', 'medicine')
            ])
            
            for lot in lots:
                # Get the original quantity from the picking attached to the PO
               po = lot.purchase_order_ids[0] if lot.purchase_order_ids else None
               if po:
                    picking = po.picking_ids[0] if po.picking_ids else None
                    if picking:
                        move_line = self.env['stock.move.line'].search([
                            ('picking_id', '=', picking.id),
                            ('lot_id', '=', lot.id)
                        ], limit=1)
                        original_qty = move_line.quantity if move_line else 0
                        current_qty = lot.product_qty
                        if current_qty < original_qty and current_qty > 0:
                            partially_consumed_batches |= lot

            
            record.partially_consumed_batch_ids = partially_consumed_batches

class VaccinationScheduleLine(models.Model):
    _name = 'vaccination.schedule.line'
    _description = 'Vaccination Schedule Line'
    _order = 'schedule_id, age_from'
    
    schedule_id = fields.Many2one(
        'vaccination.schedule',
        string='Vaccination Schedule',
        required=True,
        ondelete='cascade'
    )
    age_from = fields.Integer(
        string='Age From (Days)',
        required=True,
        help='Starting age in days'
    )
    age_to = fields.Integer(
        string='Age To (Days)',
        help='Ending age in days (for daily/continuous schedules)'
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch/Lot',
        domain=[('product_id.poultry_product_type', '=', 'medicine')],
        help='Batch or lot number of the vaccine/medicine to administer'
    )
    vaccine_product_id = fields.Many2one(
        'product.product',
        string='Vaccine/Medicine',
        domain=[('poultry_product_type', '=', 'medicine')],
        required=True,
        help='Vaccine or medicine product to administer'
    )
    quantity_per_bird = fields.Float(
        string='Quantity per Bird',
        digits=(10, 3),
        required=True,
        default=1.0,
        help='Quantity per bird'
    )
    frequency = fields.Selection([
        ('once', 'Once'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly (3 times)'),
        ('continuous', 'Continuous')
    ], string='Frequency',
       required=True,
       default='once',
       help='Administration frequency: once, daily, weekly (3x), or continuous'
    )
    purpose = fields.Char(
        string='Purpose',
        help='Purpose or disease being prevented (e.g., Newcastle Disease Prevention)'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional instructions for this age range'
    )
    
    _sql_constraints = [
        ('age_check', 'CHECK(age_to IS NULL OR age_to >= age_from)', 
         'Age To must be greater than or equal to Age From!'),
    ]
