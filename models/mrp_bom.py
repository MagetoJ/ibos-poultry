from odoo import models, fields, api, _


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_main_bom = fields.Boolean(string="Is Main BOM", default=False)