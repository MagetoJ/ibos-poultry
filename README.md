# IBOS Poultry Management System

[![License: OPL-1](https://img.shields.io/badge/License-OPL--1-blue.svg)](https://www.odoo.com/documentation/user/16.0/legal/licenses/licenses.html#odoo-apps)
[![Odoo Version](https://img.shields.io/badge/Odoo-18.0-brightgreen.svg)](https://www.odoo.com)
[![Version](https://img.shields.io/badge/version-18.0.1.2.3-orange.svg)](https://github.com/yourusername/ibos_poultry)

A comprehensive end-to-end poultry farm management solution for Odoo 18, designed to streamline operations from day-old chick receipt through growth tracking to final processing and slaughter.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Screenshots](#screenshots)
- [Technical Details](#technical-details)
- [Support](#support)
- [Credits](#credits)

## Features

### 🐣 Flock Management
- **Automatic flock creation** from purchase orders and stock receipts
- Track birds through **brooding, growth, and processing** stages
- **Real-time mortality and culling** tracking with automated quantity updates
- **Cost per bird** calculations including chick cost, feed, medicine, and gas consumption
- **Age tracking** and growth monitoring with scheduled weighing

### 📈 Growth Tracking
- Seamless transfer from **brooding to grow-out** locations
- **Location capacity management** with occupancy validation
- **Estimated slaughter date** calculation based on breed maturity
- **Dressing percentage** configuration per batch
- **Partial processing** support for gradual slaughter operations

### 🌾 Feed & Medicine Management
- Scheduled **feed consumption** tracking by flock and growth phase
- **Automatic landed cost** creation for accurate cost allocation
- **Vaccine and medicine** usage recording with batch tracking
- **Gas consumption** monitoring for heating and operations
- **Unprocessed activity dashboard** for pending tasks

### 🔪 Processing & Slaughter
- Integration with **manufacturing orders** for finished goods production
- **Bill of Materials (BOM)** support with byproduct tracking (offal, feathers, etc.)
- **Byproduct percentage** allocation with automatic main product calculation
- Batch processing with **live weight and dressed weight** recording
- State management: `confirmed` → `partially processed` → `completed`

### 💰 Financial Integration
- **Automatic landed cost** distribution for feed, medicine, and gas
- Real-time **cost per bird** calculations (processed records only)
- **Currency-aware** reporting with company currency symbols
- Integration with Odoo **accounting and asset management**

### 📊 Dashboard & Reporting
- Real-time **KPI cards**: active birds, mortality rates, current costs
- **Activity schedules**: feed, vaccine, and slaughter schedules
- **Partially processed** batch tracking
- Feed, medicine, and **combined cost reports**
- **Weight tracking** and slaughter performance reports
- All monetary values display with **company currency formatting**

### 🏭 Farm Records Management
- **Poultry location** setup with capacity tracking
- **Farm equipment** and asset management
- **Employee** assignment and scheduling
- **Feed schedule templates** (Hubbard Classic, Pilch Ross, custom)
- **Vaccination and cleaning** schedules

## Installation

### Prerequisites
- Odoo 18.0 or higher
- Python 3.10 or higher
- Required Odoo modules (automatically installed):
  - stock
  - purchase
  - mrp (Manufacturing)
  - sale_management
  - account
  - account_asset
  - hr
  - stock_landed_costs

### Install Steps

1. **Download the module**
   ```bash
   cd /path/to/odoo/addons
   git clone https://github.com/yourusername/ibos_poultry.git
   ```

2. **Restart Odoo server**
   ```bash
   sudo systemctl restart odoo
   ```

3. **Update Apps List**
   - Go to Apps menu
   - Click "Update Apps List"

4. **Install the module**
   - Search for "IBOS Poultry"
   - Click Install

## Configuration

### Initial Setup

1. **Configure Poultry Locations**
   - Go to `Poultry Management → Configuration → Poultry Locations`
   - Create locations with capacity information
   - Mark locations as brooding or grow-out spaces

2. **Set Up Product Types**
   - Go to `Inventory → Products`
   - Configure products with appropriate poultry product types:
     - `Chick` - Day-old chicks (triggers automatic flock creation)
     - `Feed` - Poultry feed
     - `Medicine` - Vaccines and medications
     - `Gas` - Heating fuel
     - `Other` - Associated costs

3. **Configure Feed Schedules** (Optional)
   - Go to `Poultry Management → Configuration → Feed Schedules`
   - Use pre-configured templates or create custom schedules
   - Available templates: Hubbard Classic, Pilch Ross

4. **Set Up Stock Locations**
   - Configure staging location for chick receipt
   - Set up loss location for mortality tracking
   - Configure raw material location for feed/medicine storage

### Bill of Materials Setup

1. Create BOMs for processing operations:
   - Product: Dressed chicken (finished good)
   - Component: Live chicken (from poultry flocks)
   - Byproducts: Offal, feathers, blood, etc.

2. Configure dressing percentages on growth tracking records

## Usage

### Daily Operations

#### 1. Receiving Chicks
1. Create purchase order for day-old chicks
2. Validate receipt → **Flock automatically created**
3. System assigns to staging/brooding location

#### 2. Feed & Medicine Recording
1. Navigate to dashboard to see scheduled activities
2. Record feed consumption:
   - `Poultry Management → Flocks → Feed Consumption`
   - Select flock/growth tracking
   - Enter quantity and product
3. System automatically creates landed costs for accurate allocation

#### 3. Transfer to Grow-Out
1. Open flock in brooding stage
2. Click "Transfer to Location"
3. Select destination location
4. System validates capacity and creates growth tracking record

#### 4. Weight Monitoring
1. Record regular weighing:
   - `Poultry Management → Flocks → Weighing Records`
   - Enter average weight and sample size
2. Track growth performance on dashboard

#### 5. Processing/Slaughter
1. Open growth tracking record
2. Click "Create Slaughter"
3. Enter processing details:
   - Quantity to process
   - BOM selection
   - Byproduct percentages
4. System creates manufacturing order
5. Validate MO to complete processing

### Reports

Access comprehensive reports:
- **Feed Consumption Report**: Track feed usage by date/flock
- **Medicine Usage Report**: Monitor vaccine and medication costs
- **Cost Report**: Combined view of all operational costs
- **Weight Report**: Growth performance analysis
- **Slaughter Report**: Processing performance metrics

## Screenshots

*Dashboard showing real-time KPIs and activity schedules*
![Dashboard](static/description/screenshot_dashboard.png)

*Flock management with cost tracking*
![Flock Management](static/description/screenshot_flock.png)

*Growth tracking with location management*
![Growth Tracking](static/description/screenshot_growth.png)

*Processing with BOM and byproduct allocation*
![Processing](static/description/screenshot_processing.png)

## Technical Details

### Architecture
- **Built on Odoo 18** with full ORM integration
- **State machine patterns** for workflow management
- **Automatic record creation** via model inheritance
- **Wizard-based operations** for complex multi-step processes
- **OWL framework dashboard** for reactive UI

### Data Flow
```
Purchase Order → Stock Picking (Receipt) → Poultry Flock → 
Growth Tracking → Manufacturing Order → Slaughter Record
```

### Key Models
- `poultry.flock` - Central entity for bird batches
- `poultry.growth.tracking` - Grow-out phase management
- `poultry.slaughter` - Processing records
- `poultry.location` - Housing locations with capacity
- `poultry.feed.consumption` - Feed tracking with landed costs
- `poultry.medicine.usage` - Vaccine and medication tracking

### Computed Fields
All cost calculations use processed records only (with landed costs and stock moves):
- `total_feed_cost` - Sum of processed feed consumption
- `total_medicine_cost` - Sum of processed medicine usage
- `current_cost_per_bird` - Total cost / initial quantity
- `current_quantity` - Initial quantity - mortality - culling

### Security
- User-level access controls via `ir.model.access.csv`
- Record rules for multi-company support
- Chatter integration for audit trails

## Support

### Documentation
- User Manual: [docs/user_manual.pdf](docs/user_manual.pdf)
- Technical Guide: [docs/technical_guide.md](docs/technical_guide.md)
- API Reference: [docs/api_reference.md](docs/api_reference.md)

### Getting Help
- **Email**: info@ibos.co.ke
- **Website**: https://www.ibos.co.ke
- **Phone**: +254 XXX XXX XXX

### Bug Reports & Feature Requests
Please submit issues through our support portal or email.

### Professional Services
IBOS offers:
- Custom module development
- Training and onboarding
- System integration
- Technical support contracts

## Credits

### Contributors
- **James Oginga** - Lead Developer[https://www.github.com/tyrmoga]
- **IBOS Team** - Architecture and Design['https://www.ibos.co.ke']

### Maintainer
**Integrity Business Outsourcing Solutions (IBOS)**

This module is maintained by IBOS Business Solutions, a leading provider of Odoo implementation and customization services in Kenya.

For support, customization, or inquiries:
- Website: https://www.ibos.co.ke
- Email: info@ibos.co.ke

## License

**OPL-1** (Odoo Proprietary License v1.0)

This module is licensed under OPL-1. See the LICENSE file for full details.

---

© 2026 Integrity Business Outsourcing Solutions. All rights reserved.
