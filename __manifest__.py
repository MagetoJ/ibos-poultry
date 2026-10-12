# -*- coding: utf-8 -*-
{
    "name": "IBOS Poultry Management System",
    "version": "18.0.1.5.7",
    "category": "Agriculture",
    "summary": "Comprehensive End-to-End Poultry Farm Management - From Chick Receipt to Processing",
    "description": """
        IBOS Poultry Management System
        ================================
        
        A complete poultry farm management solution for Odoo 18, designed to streamline operations 
        from day-old chick receipt through growth tracking to final processing and slaughter.
        
        **Key Features:**
        
        Flock Management
        ----------------
        * Automatic flock creation from purchase orders and stock receipts
        * Track birds through brooding, growth, and processing stages
        * Real-time mortality and culling tracking with automated quantity updates
        * Cost per bird calculations including chick cost, feed, medicine, and gas consumption
        * Age tracking and growth monitoring with scheduled weighing
        
        Growth Tracking
        ---------------
        * Seamless transfer from brooding to grow-out locations
        * Location capacity management with occupancy validation
        * Estimated slaughter date calculation based on breed maturity
        * Dressing percentage configuration per batch
        * Partial processing support for gradual slaughter operations
        
        Feed & Medicine Management
        --------------------------
        * Scheduled feed consumption tracking by flock and growth phase
        * Automatic landed cost creation for accurate cost allocation
        * Vaccine and medicine usage recording with batch tracking
        * Gas consumption monitoring for heating and operations
        * Unprocessed activity dashboard for pending tasks
        
        Processing & Slaughter
        ----------------------
        * Integration with manufacturing orders for finished goods production
        * Bill of Materials (BOM) support with byproduct tracking (offal, feathers, etc.)
        * Byproduct percentage allocation with automatic main product calculation
        * Batch processing with live weight and dressed weight recording
        * State management: confirmed → partially processed → completed
        
        Financial Integration
        ---------------------
        * Automatic landed cost distribution for feed, medicine, and gas
        * Real-time cost per bird calculations (processed records only)
        * Currency-aware reporting with company currency symbols
        * Integration with Odoo accounting and asset management
        
        Dashboard & Reporting
        ---------------------
        * Real-time KPI cards: active birds, mortality rates, current costs
        * Activity schedules: feed, vaccine, and slaughter schedules
        * Partially processed batch tracking
        * Feed, medicine, and combined cost reports
        * Weight tracking and slaughter performance reports
        * All monetary values display with company currency formatting
        
        Farm Records Management
        -----------------------
        * Poultry location setup with capacity tracking
        * Farm equipment and asset management
        * Employee assignment and scheduling
        * Feed schedule templates (Hubbard Classic, Pilch Ross, custom)
        * Vaccination and cleaning schedules
        
        Technical Highlights
        --------------------
        * Built on Odoo 18 with full integration to stock, purchase, MRP, sales, and accounting
        * Automatic record creation patterns for streamlined workflows
        * State machine tracking for audit trails and compliance
        * Chatter integration for communication and activity tracking
        * Wizard-based operations for complex multi-step processes
        * Custom dashboard with OWL framework for real-time updates
        * Configurable product types: chick, feed, medicine, gas, and general supplies
        
        Perfect for poultry operations of any size - from small farms to large commercial operations.
        
        **Module Dependencies:**
        * stock - Inventory management
        * purchase - Purchase orders and vendor management
        * mrp - Manufacturing orders for processing
        * sale_management - Sales integration
        * account - Financial integration
        * account_asset - Asset management for equipment
        * hr - Employee management
        * stock_landed_costs - Cost allocation
        
        For support and customization, contact IBOS at https://www.ibos.co.ke
    """,
    "author": 'Integrity Business Outsourcing Solutions',
    "maintainer": "James Oginga",
    "website": 'https://www.ibos.co.ke',
    "depends": ["stock", "sale_management", "account", "account_asset", "hr", "mail", "product", "purchase","mrp", "stock_landed_costs"],
    "data": [
        "data/sequence_data.xml",
        "data/product_data.xml",
        "data/feed_products_data.xml",
        "data/vaccine_products_data.xml",
        "data/poultry_bom_data.xml",
        "data/stock_operation_type_data.xml",
        "data/feed_schedule_hw_data.xml",
        "data/feed_schedule_pr_data.xml",
        "data/mortality_schedule_hw_data.xml",
        "data/mortality_schedule_pr_data.xml",
        "data/weight_schedule_hw_data.xml",
        "data/weight_schedule_pr_data.xml",
        "data/vaccination_schedule_broiler_data.xml",
        "data/cron_data.xml",
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/stock_location_views.xml",
        "views/stock_picking_views.xml",
        "views/account_journal.xml",
        "views/purchase_order_views.xml",
        "views/poultry_flock_views.xml",
        "views/poultry_location_views.xml",
        "views/poultry_configuration_assist_views.xml",
        "views/poultry_growth_tracking_views.xml",
        "views/poultry_feed_consumption_views.xml",
        "views/poultry_gas_consumption_views.xml",
        "views/poultry_medicine_usage_views.xml",
        "views/poultry_weighing_views.xml",
        "views/flock_transfer_wizard_views.xml",
        "views/growth_slaughter_wizard_views.xml",
        "views/mrp_production_views.xml",
        "views/poultry_slaughter_views.xml",
        "views/poultry_dashboard_views.xml",
        "views/farm_records_views.xml",
        'views/raw_material_on_hand_views.xml',
        'views/poultry_reports_views.xml',
        'views/mrp_bom_views.xml',
        "views/menu_views.xml",
    ],
    "assets": {
        'web.assets_backend': [
            'ibos_poultry/static/src/dashboard/**/*',
            'ibos_poultry/static/src/js/poultry_reports.js',
            'ibos_poultry/static/src/xml/poultry_reports.xml',
            'ibos_poultry/static/src/scss/poultry_reports.scss',
        ],
    },
    "license": "OPL-1",
    "installable": True,
    "auto_install": False,
    "application": True
}
