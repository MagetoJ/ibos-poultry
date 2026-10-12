from odoo import models, fields, api, _


class StockLocation(models.Model):
    _inherit = 'stock.location'
    
    is_staging_location = fields.Boolean(
        string='Is Brooding Location',
        default=False,
        help='Indicates if this location is used to temporarily hold the chicks before final placement in pens/houses'
    )
    is_loss_location = fields.Boolean(
        string='Is Default Inventory Loss Location',
        default=False,
        help='Indicates if this location is used to record losses of poultry due to mortality or other reasons'
    )
    is_poultry_scrap_location = fields.Boolean(
        string='Is Default Poultry Scrap Location',
        default=False,
        help='Indicates if this location is used to record scrap or loss of poultry products during processing or handling'
    )    
    is_raw_material_location = fields.Boolean(
        string='Is Poultry Raw Material Location',
        default=False,
        help='Indicates if this location is used to store poultry farm raw materials like feed, medicine, etc.'
    )