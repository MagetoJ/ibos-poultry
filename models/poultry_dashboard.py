# -*- coding: utf-8 -*-
from odoo import models, api
from datetime import datetime, timedelta


class PoultryDashboard(models.TransientModel):
    _name = 'poultry.dashboard'
    _description = 'Poultry Dashboard Data'
    def _format_currency(self, amount):
        """Format amount with company currency symbol"""
        currency = self.env.company.currency_id
        # Format with symbol before amount
        formatted = currency.format(amount)
        # Ensure symbol is at the beginning if not already
        if currency.position == 'after':
            # Move symbol from end to beginning
            formatted = f"{currency.symbol} {amount:,.2f}"
        return formatted
    @api.model
    def get_dashboard_data(self):
        """Get all dashboard statistics and data"""
        
        # Check configuration
        configuration_warning = self._check_configuration()
        
        # Get main metrics
        kpi_cards = self._get_kpi_cards()
        
        # Get detailed sections
        flocks_data = self._get_flocks_section()
        growths_data = self._get_growths_section()
        feed_schedule_data = self._get_feed_schedule_section()
        vaccine_schedule_data = self._get_vaccine_schedule_section()
        slaughter_schedule_data = self._get_slaughter_schedule_section()
        
        return {
            'company_name': self.env.company.name,
            'configuration_warning': configuration_warning,
            'kpi_cards': kpi_cards,
            'flocks': flocks_data,
            'growths': growths_data,
            'feed_schedule': feed_schedule_data,
            'vaccine_schedule': vaccine_schedule_data,
            'slaughter_schedule': slaughter_schedule_data,
        }
    
    def _check_configuration(self):
        """Check if system is properly configured"""
        has_locations = self.env['poultry.location'].search_count([]) > 0
        
        if not has_locations:
            return {
                'message': 'Setup required! Please configure your poultry locations to start.',
                'action': 'poultry_configuration_assist',
                'action_label': 'Setup Now'
            }
        return None
    
    def _get_kpi_cards(self):
        """Get Key Performance Indicators for dashboard cards"""
        # New flocks in brooding stage
        new_flocks = self.env['poultry.flock'].search([
            ('state', '=', 'received')
        ])
        new_flocks_count = len(new_flocks)
        new_flocks_birds = sum(new_flocks.mapped('current_quantity'))
        
        active_flocks = self.env['poultry.flock'].search([
            ('state', 'in', ['growing',])
        ])        
        # Calculate totals from brooder flocks
        total_birds = sum(active_flocks.mapped('current_quantity'))
        total_flocks = len(active_flocks)

        active_growths = self.env['poultry.growth.tracking'].search([
            ('state', 'in', ['confirmed','partially_processed'])
        ])
        # Calculate totals from grower flocks
        total_growing_birds = sum(active_growths.mapped('current_quantity'))
        total_growths = len(active_growths)
        
        # Calculate average mortality across both phases
        brooder_mortality_sum = sum(active_flocks.mapped('mortality_rate'))
        grower_mortality_sum = sum(active_growths.mapped('mortality_rate'))
        total_phases = total_flocks + total_growths
        avg_mortality = (brooder_mortality_sum + grower_mortality_sum) / total_phases if total_phases > 0 else 0
        
        # Get location occupancy
        locations = self.env['poultry.location'].search([])
        total_capacity = sum(locations.mapped('capacity'))
        total_occupied = sum(locations.mapped('current_occupancy'))
        occupancy_rate = (total_occupied / total_capacity * 100) if total_capacity > 0 else 0
        
        # Cost summary from both brooder and grower flocks
        brooder_feed_cost = sum(active_flocks.mapped('total_feed_cost'))
        brooder_medicine_cost = sum(active_flocks.mapped('total_medicine_cost'))
        brooder_total_cost = sum(active_flocks.mapped('total_cost'))
        
        grower_feed_cost = sum(active_growths.mapped('total_feed_cost'))
        grower_medicine_cost = sum(active_growths.mapped('total_medicine_cost'))
        grower_total_cost = sum(active_growths.mapped('total_cost'))
        
        total_feed_cost = brooder_feed_cost + grower_feed_cost
        total_medicine_cost = brooder_medicine_cost + grower_medicine_cost
        total_cost = brooder_total_cost + grower_total_cost
        
        return [
            {
                'id': 'new_flocks',
                'title': 'New Flocks',
                'value': new_flocks_count,
                'subtitle': f'{new_flocks_birds:,} birds in brooding stage',
                'icon': 'fa-plus-circle',
                'color': 'warning',
                'action': {
                    'type': 'ir.actions.act_window',
                    'name': 'New Flocks',
                    'res_model': 'poultry.flock',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [['state', '=', 'received']],
                    'context': {},
                },
            },
            {
                'id': 'total_birds',
                'title': 'Total Birds',
                'value': total_birds + total_growing_birds,
                'subtitle': f'Brooder: {total_birds:,} ({total_flocks} flocks) | Grower: {total_growing_birds:,} ({total_growths} flocks)',
                'icon': 'fa-users',
                'color': 'primary',
            },
            {
                'id': 'mortality',
                'title': 'Avg Mortality Rate',
                'value': f'{round(avg_mortality, 2)}%',
                'subtitle': f'Brooder: {round(brooder_mortality_sum / total_flocks if total_flocks > 0 else 0, 2)}% | Grower: {round(grower_mortality_sum / total_growths if total_growths > 0 else 0, 2)}%',
                'icon': 'fa-heartbeat',
                'color': 'danger',
            },
            {
                'id': 'costs',
                'title': 'Current Cost on Active Flocks',
                'value': self._format_currency(total_cost),
                'subtitle': f'Feed: {self._format_currency(total_feed_cost)} | Medicine: {self._format_currency(total_medicine_cost)}',
                'icon': 'fa-dollar',
                'color': 'info',
            },
        ]
    
    def _get_feed_schedule_section(self):
        """Get upcoming feed consumption activities"""
        today = datetime.now().date()
        all_feed_records = []
        # Get only unprocessed feed consumption records (both fields must be False)
        flock_feed_records = self.env['poultry.feed.consumption'].search([
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
            ('flock_id.active', '=', True),
            ('flock_id.state', '=', 'growing'),
        ], order='flock_id, growth_tracking_id, date asc')
        growth_feed_records = self.env['poultry.growth.feed.consumption'].search([
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
            ('growth_tracking_id.active', '=', True),
            ('growth_tracking_id.state', 'in', ['confirmed', 'partially_processed']),
        ], order='growth_tracking_id, date asc')
        all_feed_records.extend(flock_feed_records)
        all_feed_records.extend(growth_feed_records)
        upcoming_today = []
        overdue = []
        
        for record in all_feed_records:
            record_date = record.date
            
            # Determine source (Flock or Growth Tracking) and age
            source_name = ''
            age_days = 0
            flock_id = None
            growth_tracking_id = None
            
            if record.growth_tracking_id:
                source_name = f"{record.growth_tracking_id.batch_number} (Growth)"
                age_days = record.growth_tracking_id.age_days
                growth_tracking_id = record.growth_tracking_id.id
            elif record.flock_id:
                source_name = f"{record.flock_id.name} (Flock)"
                age_days = record.flock_id.age_days
                flock_id = record.flock_id.id
            
            # Skip records with zero quantity
            if record.quantity <= 0:
                continue
            
            item = {
                'id': record.id,
                'date': record_date.strftime('%Y-%m-%d'),
                'product': record.product_id.name,
                'quantity': record.quantity,
                'uom': record.uom_id.name,
                'source': source_name,
                'age': age_days,
                'flock_id': flock_id,
                'growth_tracking_id': growth_tracking_id,
            }
            
            if record_date == today:
                upcoming_today.append(item)
            elif record_date < today:
                overdue.append(item)
        
        return {
            'total': len(upcoming_today) + len(overdue),
            'upcoming_today': upcoming_today,
            'overdue': overdue,
        }
    
    def _get_vaccine_schedule_section(self):
        """Get upcoming medicine/vaccine activities"""
        today = datetime.now().date()
        all_medicine_records = []
        # Get only unprocessed medicine/vaccine records (both fields must be False)
        flock_medicine_records = self.env['poultry.medicine.usage'].search([
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
            ('flock_id.active', '=', True),
            ('flock_id.state', '=', 'growing'),
        ], order='flock_id, growth_tracking_id, date asc')
        all_medicine_records.extend(flock_medicine_records)
        growth_medicine_records = self.env['poultry.growth.medicine.usage'].search([
            ('landed_cost_id', '=', False),
            ('stock_move_id', '=', False),
            ('growth_tracking_id.active', '=', True),
            ('growth_tracking_id.state', 'in', ['confirmed', 'partially_processed']),
        ], order='growth_tracking_id, date asc')
        all_medicine_records.extend(growth_medicine_records)
        
        upcoming_today = []
        overdue = []
        
        for record in all_medicine_records:
            record_date = record.date
            
            # Determine source (Flock or Growth Tracking) and age
            source_name = ''
            age_days = 0
            flock_id = None
            growth_tracking_id = None
            
            if record.growth_tracking_id:
                source_name = f"{record.growth_tracking_id.batch_number} (Growth)"
                age_days = record.growth_tracking_id.age_days
                growth_tracking_id = record.growth_tracking_id.id
            elif record.flock_id:
                source_name = f"{record.flock_id.name} (Flock)"
                age_days = record.flock_id.age_days
                flock_id = record.flock_id.id
            
            # Skip records with zero quantity
            if record.quantity <= 0:
                continue
            
            item = {
                'id': record.id,
                'date': record_date.strftime('%Y-%m-%d'),
                'product': record.product_id.name,
                'quantity': record.quantity,
                'uom': record.uom_id.name,
                'purpose': record.purpose or '',
                'source': source_name,
                'age': age_days,
                'flock_id': flock_id,
                'growth_tracking_id': growth_tracking_id,
            }
            
            if record_date == today:
                upcoming_today.append(item)
            elif record_date < today:
                overdue.append(item)
        
        return {
            'total': len(upcoming_today) + len(overdue),
            'upcoming_today': upcoming_today,
            'overdue': overdue,
        }
    
    def _get_slaughter_schedule_section(self):
        """Get upcoming slaughter schedule from growth tracking"""
        today = datetime.now().date()
        
        # Get active growth tracking records with slaughter dates
        growth_records = self.env['poultry.growth.tracking'].search([
            ('state', 'in', ['confirmed', 'partially_processed']),
            ('estimated_slaughter_date', '!=', False),
        ], order='estimated_slaughter_date asc')
        
        upcoming = []
        overdue = []
        partially_processed = []
        
        for record in growth_records:
            slaughter_date = record.estimated_slaughter_date
            
            # Check if there are any slaughter records for this growth tracking
            slaughter_count = self.env['poultry.slaughter'].search_count([
                ('growth_tracking_id', '=', record.id),
            ])
            
            # If there are slaughter records but state is still confirmed, treat as partially processed
            is_partially_processed = record.state == 'partially_processed' or (record.state == 'confirmed' and slaughter_count > 0)
            
            item = {
                'id': record.id,
                'date': slaughter_date.strftime('%Y-%m-%d'),
                'batch_number': record.name if record.flock_id.growth_tracking_count else record.batch_number,
                'flock_name': record.flock_id.name if record.flock_id else '',
                'birds': record.current_quantity,
                'age': record.age_days,
                'location': record.poultry_location_id.name if record.poultry_location_id else '',
                'state': record.state,
            }
            
            # Separate by whether it's partially processed first (has slaughter records)
            if is_partially_processed:
                partially_processed.append(item)
            elif slaughter_date == today:
                upcoming.append(item)
            elif slaughter_date < today:
                overdue.append(item)
            else:
                upcoming.append(item)
        
        return {
            'total': len(upcoming) + len(overdue) + len(partially_processed),
            'upcoming': upcoming,
            'overdue': overdue,
            'partially_processed': partially_processed,
        }
    
    def _get_flocks_section(self):
        """Get active flocks data"""
        active_flocks = self.env['poultry.flock'].search([
            ('state', 'in', ['growing'])
        ], order='mortality_rate asc, name asc', limit=10)
        
        flocks_list = [{
            'id': flock.id,
            'name': flock.name,
            'location': flock.poultry_location_id.name if flock.poultry_location_id else '',
            'birds': flock.current_quantity,
            'age_days': flock.age_days,
            'mortality_rate': round(flock.mortality_rate, 2),
            'cost_per_bird': round(flock.current_cost_per_bird, 2),
        } for flock in active_flocks]
        
        return {
            'total': len(active_flocks),
            'list': flocks_list,
        }
    
    def _get_growths_section(self):
        """Get active growth tracking data"""
        active_growths = self.env['poultry.growth.tracking'].search([
            ('state', 'in', ['confirmed', 'partially_processed'])
        ], order='mortality_rate asc, batch_number asc', limit=10)
        
        growths_list = [{
            'id': growth.id,
            'batch_number': growth.batch_number,
            'location': growth.poultry_location_id.name if growth.poultry_location_id else '',
            'birds': growth.current_quantity,
            'age_days': growth.age_days,
            'mortality_rate': round(growth.mortality_rate, 2),
            'cost_per_bird': round(growth.cost_per_bird, 2),
        } for growth in active_growths]
        
        return {
            'total': len(active_growths),
            'list': growths_list,
        }
    
    def _get_locations_section(self):
        """Get locations status"""
        locations = self.env['poultry.location'].search([], order='name')
        
        locations_list = [{
            'id': loc.id,
            'name': loc.name,
            'capacity': loc.capacity,
            'occupied': loc.current_occupancy,
            'available': loc.capacity - loc.current_occupancy,
            'occupancy_pct': round((loc.current_occupancy / loc.capacity * 100) if loc.capacity > 0 else 0, 1),
        } for loc in locations]
        
        return {
            'total': len(locations),
            'list': locations_list,
        }
