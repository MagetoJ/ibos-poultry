/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PoultryReportView extends Component {
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        updateActionState: { type: Function, optional: true },
        className: { type: String, optional: true },
        "*": true,  // Allow any additional props
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            report_data: {
                report_name: "Poultry Reports",
                columns: [],
                lines: [],
                options: {}
            },
            loading: false,
            flocks: [],
            locations: [],
            show_closed_flocks: false,
        });

        onWillStart(async () => {
            await this.loadFlocks();
            await this.loadLocations();
            await this.loadReport();
        });
    }

    async loadReport(options = null) {
        this.state.loading = true;
        try {
            const reportOptions = options || this.getDefaultOptions();
            const data = await this.orm.call(
                "poultry.reports",
                "get_report_data",
                [reportOptions]
            );
            this.state.report_data = data;
        } catch (error) {
            console.error("Error loading report:", error);
        } finally {
            this.state.loading = false;
        }
    }

    getDefaultOptions() {
        const today = new Date();
        const lastMonth = new Date(today);
        lastMonth.setDate(today.getDate() - 30);
        
        return {
            date: {
                date_from: this.formatDate(lastMonth),
                date_to: this.formatDate(today),
                filter: 'custom',
            },
            location_id: false,
            flock_id: false,
            report_type: 'cost',
        };
    }

    formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    async onDateChange(ev) {
        const field = ev.target.dataset.field;
        const value = ev.target.value;
        
        const options = this.getCurrentOptions();
        if (!options.date) {
            options.date = {};
        }
        options.date[field] = value;
        
        await this.loadReport(options);
    }

    async onLocationChange(ev) {
        const locationId = ev.target.value ? parseInt(ev.target.value) : false;
        
        const options = this.getCurrentOptions();
        options.location_id = locationId;
        
        await this.loadReport(options);
    }

    async onReportTypeChange(ev) {
        const reportType = ev.target.value;
        
        const options = this.getCurrentOptions();
        options.report_type = reportType;
        
        await this.loadReport(options);
    }

    async onFlockChange(ev) {
        const flockId = ev.target.value ? parseInt(ev.target.value) : false;
        
        const options = this.getCurrentOptions();
        options.flock_id = flockId;
        
        await this.loadReport(options);
    }

    async onShowClosedFlocksChange(ev) {
        this.state.show_closed_flocks = ev.target.checked;
        await this.loadFlocks();
    }

    getCurrentOptions() {
        // Get current options from state or use defaults
        if (this.state.report_data && this.state.report_data.options) {
            return JSON.parse(JSON.stringify(this.state.report_data.options));
        }
        return this.getDefaultOptions();
    }

    async loadFlocks() {
        try {
            const domain = this.state.show_closed_flocks ? [] : [['state', '!=', 'closed']];
            const flocks = await this.orm.searchRead(
                "poultry.flock",
                domain,
                ["id", "name"],
                { order: "name" }
            );
            this.state.flocks = flocks;
        } catch (error) {
            console.error("Error loading flocks:", error);
            this.state.flocks = [];
        }
    }

    async loadLocations() {
        try {
            const locations = await this.orm.searchRead(
                "poultry.location",
                [],
                ["id", "name"],
                { order: "name" }
            );
            this.state.locations = locations;
        } catch (error) {
            console.error("Error loading locations:", error);
            this.state.locations = [];
        }
    }

    async onRefresh() {
        await this.loadReport(this.state.report_data.options);
    }

    async onPrint() {
        // Implement print functionality
        window.print();
    }

    async onExport() {
        // Implement export functionality
        console.log("Export functionality to be implemented");
    }
}

PoultryReportView.template = "ibos_poultry.PoultryReportView";

registry.category("actions").add("poultry_reports", PoultryReportView);
