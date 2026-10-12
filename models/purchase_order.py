# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_poultry_purchase = fields.Boolean(
        string='Is Poultry Purchase',
        compute='_compute_is_poultry_purchase',
        store=True,
        help='Indicates if this purchase order contains poultry products'
    )
    poultry_receipt_location_id = fields.Many2one(
        'stock.location',
        string='Receipt Location',
        domain=[('usage', '=', 'internal'), ('is_staging_location', '=', True)],
        help='Staging location where chicks will be received'
    )

    @api.depends('order_line.product_id.poultry_product_type')
    def _compute_is_poultry_purchase(self):
        """Check if PO contains any poultry products"""
        for order in self:
            order.is_poultry_purchase = any(
                line.product_id.poultry_product_type in ['chick', 'feed', 'medicine', 'other', 'etc']
                for line in order.order_line
            )

    # def _prepare_picking(self):
    #     """Override to set destination location for poultry receipts"""
    #     res = super()._prepare_picking()
    #     if self.is_poultry_purchase and self.poultry_receipt_location_id:
    #         res['location_dest_id'] = self.poultry_receipt_location_id.id
    #     return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_chick_product = fields.Boolean(
        string='Is Chick',
        compute='_compute_is_chick_product',
        store=True
    )

    price_unit_untaxed = fields.Float(
        string='Unit Price (Untaxed)',
        compute='_compute_price_unit_untaxed',
        digits='Product Price',
        help='Unit price without tax (after discount). For a tax-included '
             'price this is the vendor price minus the tax, e.g. 10.00 at 16% '
             'included VAT = 8.62. This is the cost the poultry module records.'
    )

    @api.depends('price_subtotal', 'product_qty', 'price_unit', 'discount')
    def _compute_price_unit_untaxed(self):
        for line in self:
            if line.display_type:
                line.price_unit_untaxed = 0.0
            elif line.product_qty:
                line.price_unit_untaxed = line.price_subtotal / line.product_qty
            else:
                line.price_unit_untaxed = line.price_unit * (1 - (line.discount or 0.0) / 100.0)

    @api.depends('product_id.poultry_product_type')
    def _compute_is_chick_product(self):
        """Check if line is for chick product"""
        for line in self:
            line.is_chick_product = line.product_id.poultry_product_type == 'chick'
