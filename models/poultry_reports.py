# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from collections import defaultdict


class PoultryReports(models.AbstractModel):
    _name = 'poultry.reports'
    _description = 'Poultry Dynamic Reports'

    filter_date_from = None
    filter_date_to = None
    filter_location_id = None
    filter_report_type = 'cost'

    def _get_options(self, previous_options=None):
        """Get report options with filters"""
        if previous_options is None:
            previous_options = {}
        
        today = fields.Date.today()
        
        options = {
            'date': {
                'date_from': previous_options.get('date', {}).get('date_from', 
                    fields.Date.to_string(today - timedelta(days=30))),
                'date_to': previous_options.get('date', {}).get('date_to', 
                    fields.Date.to_string(today)),
                'filter': previous_options.get('date', {}).get('filter', 'custom'),
            },
            'location_id': previous_options.get('location_id', False),
            'report_type': previous_options.get('report_type', 'cost'),
        }
        
        return options

    def _get_report_name(self):
        """Get report name"""
        return _('Poultry Reports')

    def _get_cost_report_products(self):
        """Get all products used for cost report columns"""
        return self.env['product.product'].search([
            ('poultry_product_type', 'in', ['feed', 'medicine', 'gas','etc','other'])
        ], order='name')

    def _get_columns_name(self, options):
        """Get column headers based on report type"""
        report_type = options.get('report_type', 'cost')
        
        if report_type == 'slaughter':
            return [
                {'name': _('Date'), 'class': 'date'},
                {'name': _('Flock'), 'class': ''},
                {'name': _('Qty Slaughtered'), 'class': 'number'},
                {'name': _('Live Weight (kg)'), 'class': 'number'},
            ]
        elif report_type == 'feed':
            return [
                {'name': _('Date'), 'class': 'date'},
                {'name': _('Flock'), 'class': ''},
                {'name': _('Total Feed Cost'), 'class': 'number'},
            ]
        elif report_type == 'medicine':
            return [
                {'name': _('Date'), 'class': 'date'},
                {'name': _('Flock'), 'class': ''},
                {'name': _('Total Medicine Cost'), 'class': 'number'},
            ]
        elif report_type == 'weight':
            return [
                {'name': _('Date'), 'class': 'date'},
                {'name': _('Flock'), 'class': ''},
                {'name': _('Age (Days)'), 'class': 'number'},
                {'name': _('Quantity'), 'class': 'number'},
                {'name': _('Avg Weight (g)'), 'class': 'number'},
                {'name': _('Total Weight (kg)'), 'class': 'number'},
            ]
        elif report_type == 'cost':
            return [
                {'name': _('Date'), 'class': 'date'},
                {'name': _('Flock'), 'class': ''},
                {'name': _('Feed Cost'), 'class': 'number'},
                {'name': _('Medicine Cost'), 'class': 'number'},
                {'name': _('Total'), 'class': 'number total'},
            ]
        else:
            return [
                {'name': _('Date'), 'class': 'date'},
                {'name': _('Description'), 'class': ''},
                {'name': _('Value'), 'class': 'number'},
            ]

    def _get_lines(self, options):
        """Get report lines based on report type"""
        report_type = options.get('report_type', 'cost')
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        location_id = options.get('location_id')
        flock_id = options.get('flock_id')
        
        if report_type == 'slaughter':
            return self._get_slaughter_lines(date_from, date_to, location_id, flock_id)
        elif report_type == 'feed':
            return self._get_feed_lines(date_from, date_to, location_id, flock_id)
        elif report_type == 'medicine':
            return self._get_medicine_lines(date_from, date_to, location_id, flock_id)
        elif report_type == 'weight':
            return self._get_weight_lines(date_from, date_to, location_id, flock_id)
        elif report_type == 'cost':
            return self._get_cost_lines(date_from, date_to, location_id, flock_id)
        else:
            return []

    def _get_slaughter_lines(self, date_from, date_to, location_id, flock_id):
        """Get slaughter report lines in pivot format by date and flock"""
        
        domain = [
            ('slaughter_date', '>=', date_from),
            ('slaughter_date', '<=', date_to),
        ]
        if flock_id:
            domain.append(('flock_id', '=', flock_id))
        elif location_id:
            domain.append(('poultry_location_id', '=', location_id))
        
        slaughter_records = self.env['poultry.slaughter'].search(domain, order='slaughter_date desc')
        
        # Group by (date, flock)
        data_grid = defaultdict(lambda: {
            'qty': 0,
            'live_weight': 0,
        })
        flock_names = {}
        
        for record in slaughter_records:
            flock = record.flock_id
            flock_key = flock.id if flock else 0
            flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.slaughter_date, flock_key)
            data_grid[key]['qty'] += record.quantity_slaughtered
            data_grid[key]['live_weight'] += record.total_live_weight / 1000
        
        lines = []
        totals = {'qty': 0, 'live_weight': 0}
        
        # Sort by date (most recent first), then by flock name
        sorted_keys = sorted(data_grid.keys(), key=lambda x: (x[0], flock_names.get(x[1], '')), reverse=True)
        
        for date, flock_key in sorted_keys:
            data = data_grid[(date, flock_key)]
            
            lines.append({
                'id': f'slaughter_{date}_{flock_key}',
                'name': date,
                'columns': [
                    {'name': date},
                    {'name': flock_names.get(flock_key, _('No Flock'))},
                    {'name': self.format_value(data['qty']), 'class': 'number'},
                    {'name': self.format_value(data['live_weight'], digits=2), 'class': 'number'},
                ],
                'level': 2,
            })
            
            for key in totals:
                totals[key] += data[key]
        
        # Add total line
        if lines:
            lines.append({
                'id': 'total',
                'name': _('Total'),
                'columns': [
                    {'name': ''},
                    {'name': _('Total'), 'class': 'fw-bold'},
                    {'name': self.format_value(totals['qty']), 'class': 'number fw-bold'},
                    {'name': self.format_value(totals['live_weight'], digits=2), 'class': 'number fw-bold'},
                ],
                'level': 1,
                'class': 'total',
            })
        
        return lines

    def _get_feed_lines(self, date_from, date_to, location_id, flock_id):
        """Get feed consumption report lines grouped by date and flock"""
       
        # Flock-level domain
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            domain.extend(['|', ('flock_id', '=', flock_id), ('growth_tracking_id.flock_id', '=', flock_id)])
        elif location_id:
            domain.append(('poultry_location_id', '=', location_id))
        
        # Growth-level domain (no flock_id field)
        growth_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            growth_domain.append(('growth_tracking_id.flock_id', '=', flock_id))
        elif location_id:
            growth_domain.append(('growth_tracking_id.poultry_location_id', '=', location_id))
        
        # Search both flock-level and growth-level feed consumption
        flock_feed_records = self.env['poultry.feed.consumption'].search(domain)
        growth_feed_records = self.env['poultry.growth.feed.consumption'].search(growth_domain)
        
        # Group by (date, flock): {(date, flock_id): total_cost}
        data_grid = defaultdict(float)
        flock_names = {}
        
        for record in flock_feed_records:
            flock = record.flock_id or (record.growth_tracking_id.flock_id if record.growth_tracking_id else None)
            flock_key = flock.id if flock else 0
            flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key] += record.total_cost
        
        # Process growth-level feed records
        for record in growth_feed_records:
            flock = record.growth_tracking_id.flock_id if record.growth_tracking_id else None
            flock_key = flock.id if flock else 0
            if flock_key not in flock_names:
                flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key] += record.total_cost
        
        lines = []
        grand_total = 0
        
        # Sort by date (most recent first), then by flock name
        sorted_keys = sorted(data_grid.keys(), key=lambda x: (x[0], flock_names.get(x[1], '')), reverse=True)
        
        for date, flock_key in sorted_keys:
            cost = data_grid[(date, flock_key)]
            grand_total += cost
            
            lines.append({
                'id': f'feed_{date}_{flock_key}',
                'name': date,
                'columns': [
                    {'name': date},
                    {'name': flock_names.get(flock_key, _('No Flock'))},
                    {'name': self.format_value(cost, is_currency=True), 'class': 'number'},
                ],
                'level': 2,
            })
        
        # Add total row
        if lines:
            lines.append({
                'id': 'total',
                'name': _('Total'),
                'columns': [
                    {'name': ''},
                    {'name': _('Total'), 'class': 'fw-bold'},
                    {'name': self.format_value(grand_total, digits=2), 'class': 'number fw-bold'},
                ],
                'level': 1,
                'class': 'total',
            })
        
        return lines

    def _get_medicine_lines(self, date_from, date_to, location_id, flock_id):
        """Get medicine usage report lines grouped by date and flock"""
        from collections import defaultdict
        
        # Flock-level domain
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            domain.extend(['|', ('flock_id', '=', flock_id), ('growth_tracking_id.flock_id', '=', flock_id)])
        elif location_id:
            domain.append(('poultry_location_id', '=', location_id))
        
        # Growth-level domain (no flock_id field)
        growth_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            growth_domain.append(('growth_tracking_id.flock_id', '=', flock_id))
        elif location_id:
            growth_domain.append(('growth_tracking_id.poultry_location_id', '=', location_id))
        
        # Search both flock-level and growth-level medicine usage
        medicine_records = self.env['poultry.medicine.usage'].search(domain)
        growth_medicine_records = self.env['poultry.growth.medicine.usage'].search(growth_domain)
        
        # Group by (date, flock): {(date, flock_id): total_cost}
        data_grid = defaultdict(float)
        flock_names = {}
        
        for record in medicine_records:
            flock = record.flock_id or (record.growth_tracking_id.flock_id if record.growth_tracking_id else None)
            flock_key = flock.id if flock else 0
            flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key] += record.total_cost
        
        # Process growth-level medicine records
        for record in growth_medicine_records:
            flock = record.growth_tracking_id.flock_id if record.growth_tracking_id else None
            flock_key = flock.id if flock else 0
            if flock_key not in flock_names:
                flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key] += record.total_cost
        
        lines = []
        grand_total = 0
        
        # Sort by date (most recent first), then by flock name
        sorted_keys = sorted(data_grid.keys(), key=lambda x: (x[0], flock_names.get(x[1], '')), reverse=True)
        
        for date, flock_key in sorted_keys:
            cost = data_grid[(date, flock_key)]
            grand_total += cost
            
            lines.append({
                'id': f'medicine_{date}_{flock_key}',
                'name': date,
                'columns': [
                    {'name': date},
                    {'name': flock_names.get(flock_key, _('No Flock'))},
                    {'name': self.format_value(cost, is_currency=True), 'class': 'number'},
                ],
                'level': 2,
            })
        
        # Add total row
        if lines:
            lines.append({
                'id': 'total',
                'name': _('Total'),
                'columns': [
                    {'name': ''},
                    {'name': _('Total'), 'class': 'fw-bold'},
                    {'name': self.format_value(grand_total, is_currency=True), 'class': 'number fw-bold'},
                ],
                'level': 1,
                'class': 'total',
            })
        
        return lines

    def _get_weight_lines(self, date_from, date_to, location_id, flock_id):
        """Get weight tracking report lines by date and flock"""
        from collections import defaultdict
        
        domain = [
            ('weighing_date', '>=', date_from),
            ('weighing_date', '<=', date_to),
        ]
        if flock_id:
            domain.extend(['|', ('flock_id', '=', flock_id), ('growth_tracking_id.flock_id', '=', flock_id)])
        elif location_id:
            domain.append(('poultry_location_id', '=', location_id))
        
        weighing_records = self.env['poultry.weighing'].search(domain, order='weighing_date desc')
        
        # Group by (date, flock)
        data_grid = defaultdict(lambda: {
            'age': 0,
            'quantity': 0,
            'weight': 0,
            'total_weight': 0,
            'count': 0
        })
        flock_names = {}
        
        for record in weighing_records:
            flock = record.flock_id or (record.growth_tracking_id.flock_id if record.growth_tracking_id else None)
            flock_key = flock.id if flock else 0
            flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            # Get age from growth tracking if available
            age = record.growth_tracking_id.age_days if record.growth_tracking_id else 0
            quantity = record.growth_tracking_id.current_quantity if record.growth_tracking_id else record.sample_size
            
            key = (record.weighing_date, flock_key)
            data_grid[key]['age'] = age  # Take latest age
            data_grid[key]['quantity'] = quantity  # Take latest quantity
            data_grid[key]['weight'] += record.average_weight
            data_grid[key]['total_weight'] += (record.average_weight * quantity / 1000)  # Convert to kg
            data_grid[key]['count'] += 1
        
        lines = []
        
        # Sort by date (most recent first), then by flock name
        sorted_keys = sorted(data_grid.keys(), key=lambda x: (x[0], flock_names.get(x[1], '')), reverse=True)
        
        for date, flock_key in sorted_keys:
            data = data_grid[(date, flock_key)]
            avg_weight = data['weight'] / data['count'] if data['count'] > 0 else 0
            
            lines.append({
                'id': f'weight_{date}_{flock_key}',
                'name': date,
                'columns': [
                    {'name': date},
                    {'name': flock_names.get(flock_key, _('No Flock'))},
                    {'name': self.format_value(data['age']), 'class': 'number'},
                    {'name': self.format_value(data['quantity']), 'class': 'number'},
                    {'name': self.format_value(avg_weight, digits=2), 'class': 'number'},
                    {'name': self.format_value(data['total_weight'], digits=2), 'class': 'number'},
                ],
                'level': 2,
            })
        
        return lines

    def _get_cost_lines(self, date_from, date_to, location_id, flock_id):
        """Get combined cost report lines showing feed and medicine totals"""
        from collections import defaultdict
        
        # Flock-level feed consumption domain
        feed_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            feed_domain.extend(['|', ('flock_id', '=', flock_id), ('growth_tracking_id.flock_id', '=', flock_id)])
        elif location_id:
            feed_domain.append(('poultry_location_id', '=', location_id))
        
        # Growth-level feed consumption domain (no flock_id field)
        growth_feed_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            growth_feed_domain.append(('growth_tracking_id.flock_id', '=', flock_id))
        elif location_id:
            growth_feed_domain.append(('growth_tracking_id.poultry_location_id', '=', location_id))
        
        # Flock-level medicine consumption domain
        medicine_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            medicine_domain.extend(['|', ('flock_id', '=', flock_id), ('growth_tracking_id.flock_id', '=', flock_id)])
        elif location_id:
            medicine_domain.append(('poultry_location_id', '=', location_id))
        
        # Growth-level medicine consumption domain (no flock_id field)
        growth_medicine_domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        if flock_id:
            growth_medicine_domain.append(('growth_tracking_id.flock_id', '=', flock_id))
        elif location_id:
            growth_medicine_domain.append(('growth_tracking_id.poultry_location_id', '=', location_id))
        
        # Group by (date, flock): {(date, flock_id): {'feed': cost, 'medicine': cost}}
        data_grid = defaultdict(lambda: {'feed': 0, 'medicine': 0})
        flock_names = {}
        
        # Get flock-level feed records
        feed_records = self.env['poultry.feed.consumption'].search(feed_domain)
        for record in feed_records:
            flock = record.flock_id or (record.growth_tracking_id.flock_id if record.growth_tracking_id else None)
            flock_key = flock.id if flock else 0
            flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key]['feed'] += record.total_cost
        
        # Get growth-level feed records
        growth_feed_records = self.env['poultry.growth.feed.consumption'].search(growth_feed_domain)
        for record in growth_feed_records:
            flock = record.growth_tracking_id.flock_id if record.growth_tracking_id else None
            flock_key = flock.id if flock else 0
            if flock_key not in flock_names:
                flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key]['feed'] += record.total_cost
        
        # Get flock-level medicine records
        medicine_records = self.env['poultry.medicine.usage'].search(medicine_domain)
        for record in medicine_records:
            flock = record.flock_id or (record.growth_tracking_id.flock_id if record.growth_tracking_id else None)
            flock_key = flock.id if flock else 0
            flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key]['medicine'] += record.total_cost
        
        # Get growth-level medicine records
        growth_medicine_records = self.env['poultry.growth.medicine.usage'].search(growth_medicine_domain)
        for record in growth_medicine_records:
            flock = record.growth_tracking_id.flock_id if record.growth_tracking_id else None
            flock_key = flock.id if flock else 0
            if flock_key not in flock_names:
                flock_names[flock_key] = flock.name if flock else _('No Flock')
            
            key = (record.date, flock_key)
            data_grid[key]['medicine'] += record.total_cost
        
        lines = []
        totals = {'feed': 0, 'medicine': 0}
        
        # Sort by date (most recent first), then by flock name
        sorted_keys = sorted(data_grid.keys(), key=lambda x: (x[0], flock_names.get(x[1], '')), reverse=True)
        
        for date, flock_key in sorted_keys:
            feed_cost = data_grid[(date, flock_key)]['feed']
            medicine_cost = data_grid[(date, flock_key)]['medicine']
            row_total = feed_cost + medicine_cost
            
            totals['feed'] += feed_cost
            totals['medicine'] += medicine_cost
            
            lines.append({
                'id': f'cost_{date}_{flock_key}',
                'name': date,
                'columns': [
                    {'name': date},
                    {'name': flock_names.get(flock_key, _('No Flock'))},
                    {'name': self.format_value(feed_cost, is_currency=True) if feed_cost else '', 'class': 'number'},
                    {'name': self.format_value(medicine_cost, is_currency=True) if medicine_cost else '', 'class': 'number'},
                    {'name': self.format_value(row_total, is_currency=True), 'class': 'number'},
                ],
                'level': 2,
            })
        
        # Add total row
        if lines:
            grand_total = totals['feed'] + totals['medicine']
            lines.append({
                'id': 'total',
                'name': _('Total'),
                'columns': [
                    {'name': ''},
                    {'name': _('Total'), 'class': 'fw-bold'},
                    {'name': self.format_value(totals['feed'], is_currency=True), 'class': 'number fw-bold'},
                    {'name': self.format_value(totals['medicine'], is_currency=True), 'class': 'number fw-bold'},
                    {'name': self.format_value(grand_total, is_currency=True), 'class': 'number fw-bold'},
                ],
                'level': 1,
                'class': 'total',
            })
        
        return lines

    def format_value(self, value, digits=0, is_currency=False):
        """Format numeric values"""
        if value is False or value is None:
            return ''
        
        if is_currency:
            currency = self.env.company.currency_id
            # Format with symbol before amount
            formatted = f"{currency.symbol} {value:,.2f}"
            return formatted
        
        if digits:
            return f'{value:,.{digits}f}'
        return f'{int(value):,}'

    @api.model
    def get_report_data(self, options):
        """Get complete report data - API endpoint"""
        return {
            'report_name': self._get_report_name(),
            'columns': self._get_columns_name(options),
            'lines': self._get_lines(options),
            'options': options,
        }