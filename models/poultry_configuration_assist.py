# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PoultryConfigurationAssist(models.Model):
    _name = 'poultry.configuration.assist'
    _description = 'Poultry Configuration Assistant'
    _rec_name = 'warehouse_id'
    
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Select Warehouse',
        required=True,
        help='Choose the warehouse to configure locations for'
    )
    
    location_line_ids = fields.One2many(
        'poultry.configuration.assist.line',
        'wizard_id',
        string='Location Configuration'
    )
    default_raw_material_location_id = fields.Many2one(
        'stock.location',
        string='Default Raw Material Location',
        domain=[('usage', '=', 'internal'), ('is_raw_material_location', '=', True)],
        help='Default location for poultry raw materials'
    )

    default_scrap_location_id = fields.Many2one(
        'stock.location',
        string='Default Scrap Location',
        domain=['|',('is_poultry_scrap_location', '=', True),('scrap_location', '=', True)],
        help='Default location for poultry scrap or loss'
    )   
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        """Load all child locations of selected warehouse"""
        if self.warehouse_id:
            # Get all internal child locations of warehouse
            locations = self.env['stock.location'].search([
                ('location_id', 'child_of', self.warehouse_id.lot_stock_id.id),
                ('usage', '=', 'internal')
            ])
            
            # Create lines for each location
            lines = []
            for location in locations:
                # Check if poultry location already exists
                existing = self.env['poultry.location'].search([
                    ('stock_location_id', '=', location.id)
                ], limit=1)
                
                if not existing:
                    lines.append((0, 0, {
                        'location_id': location.id,
                        'code': location.name,
                        'location_type': 'indoor',
                        'capacity': 0,
                    }))
            
            self.location_line_ids = lines
        else:
            self.location_line_ids = False
    
    def action_configure(self):
        """Create poultry locations from configured lines"""
        self.ensure_one()
        
        # Create default loss location if it doesn't exist
        self.action_create_default_loss_location()
        
        if not self.location_line_ids:
            raise ValidationError(_('No locations to configure. Please select a warehouse with available locations.'))
        
        created_locations = []
        for line in self.location_line_ids:
            if line.capacity <= 0:
                raise ValidationError(_('Please set the capacity for location %s.') % line.location_id.name)
            # Skip lines without required fields
            if not line.location_id or not line.code:
                continue
                
            # Check if poultry location already exists
            existing = self.env['poultry.location'].search([
                ('stock_location_id', '=', line.location_id.id)
            ], limit=1)
            
            if existing:
                continue
            
            # Create poultry location
            poultry_location = self.env['poultry.location'].create({
                'name': line.location_id.name,
                'code': line.code,
                'stock_location_id': line.location_id.id,
                'capacity': line.capacity,
                'location_type': line.location_type,
            })
            created_locations.append(poultry_location.id)
        
        if not created_locations:
            raise ValidationError(_('No poultry locations were created. Please check your configuration.'))
        
        # Open created poultry locations
        return {
            'name': _('Poultry Locations'),
            'type': 'ir.actions.act_window',
            'res_model': 'poultry.location',
            'domain': [('id', 'in', created_locations)],
            'view_mode': 'list,form',
            'target': 'current',
        }
    
    def action_create_new_location(self):
        """Open form to create a new stock location under warehouse"""
        self.ensure_one()
        if not self.warehouse_id:
            raise ValidationError(_('Please select a warehouse first.'))
        
        return {
            'name': _('Create New Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.location',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_location_id': self.warehouse_id.lot_stock_id.id,
                'default_usage': 'internal',
                'default_company_id': self.company_id.id,
            }
        }
    def action_create_default_loss_location(self):
        """Create a default internal consumption location if not exists"""
        self.ensure_one()
        if not self.warehouse_id:
            raise ValidationError(_('Please select a warehouse first.'))
        
        # Check if a loss location already exists
        existing = self.env['stock.location'].search([
            ('is_loss_location', '=', True),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if existing:
            # Location already exists, return silently
            return False
        
        # Find or create Virtual Locations parent
        virtual_parent = self.env['stock.location'].search([
            ('name', '=', 'Virtual Locations'),
            ('usage', '=', 'view'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not virtual_parent:
            # Create Virtual Locations parent
            virtual_parent = self.env['stock.location'].create({
                'name': 'Virtual Locations',
                'usage': 'view',
                'company_id': self.company_id.id,
            })
        
        # Get default COGS account
        cogs_account = self.env['account.account'].search([
            ('internal_group', '=', 'expense'),
            ('account_type', '=', 'expense_direct_cost')
        ], limit=1)
        
        # Create new stock location under Virtual Locations
        location_vals = {
            'name': _('Internal Consumption - %s') % self.warehouse_id.name,
            'location_id': virtual_parent.id,
            'usage': 'inventory',
            'is_loss_location': True,
            'company_id': self.company_id.id,
        }
        
        # Add valuation accounts if COGS account found
        if cogs_account:
            location_vals['valuation_in_account_id'] = cogs_account.id
            location_vals['valuation_out_account_id'] = cogs_account.id
        
        loss_location = self.env['stock.location'].create(location_vals)
        
        return {
            'name': _('Internal Consumption Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.location',
            'view_mode': 'form',
            'res_id': loss_location.id,
            'target': 'current',
        }


class PoultryConfigurationAssistLine(models.Model):
    _name = 'poultry.configuration.assist.line'
    _description = 'Poultry Configuration Line'
    
    wizard_id = fields.Many2one(
        'poultry.configuration.assist',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Stock Location',
        domain="[('usage', '=', 'internal')]",  
        required=True,
    )
    code = fields.Char(
        string='Code',
        required=True
    )
    location_type = fields.Selection([
        ('indoor', 'Indoor Location'),
        ('outdoor', 'Outdoor Location'),
    ], string='Location Type',
       required=True,
       default='indoor'
    )
    capacity = fields.Integer(
        string='Capacity',
        help='Maximum number of birds',
        required=True,
    )
