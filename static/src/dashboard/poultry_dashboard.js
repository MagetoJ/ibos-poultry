/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PoultryDashboard extends Component {
    static template = "ibos_poultry.PoultryDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: null,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "poultry.dashboard",
                "get_dashboard_data",
                []
            );
        } finally {
            this.state.loading = false;
        }
    }

    async refreshDashboard() {
        await this.loadData();
    }

    handleCardAction(action) {
        // If action is an object (from Python backend), execute it directly
        if (typeof action === 'object' && action.type) {
            this.action.doAction(action);
            return;
        }
        
        // Legacy string-based actions
        if (action === 'open_flocks') {
            this.openFlocks();
        } else if (action === 'open_growths') {
            this.openGrowths();
        } else if (action === 'open_locations') {
            this.openLocations();
        }
    }

    openConfiguration() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "poultry.configuration.assist",
            views: [[false, "form"]],
            target: "new",
            name: "Setup Poultry Locations",
        });
    }

    openFlocks() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "poultry.flock",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["growing", "transfer"]]],
            name: "Active Brooder Flocks",
        });
    }

    openGrowths() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "poultry.growth.tracking",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["confirmed", "partially_processed"]]],
            name: "Active Grower Flocks",
        });
    }

    openLocations() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "poultry.location",
            views: [[false, "list"], [false, "form"]],
            name: "Poultry Locations",
        });
    }

    openFlock(flockId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "poultry.flock",
            res_id: flockId,
            views: [[false, "form"]],
        });
    }
    
    openGrowth(growthId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "poultry.growth.tracking",
            res_id: growthId,
            views: [[false, "form"]],
        });
    }
    
    openFeedRecord(item) {
        // Open the flock or growth tracking record
        if (item.growth_tracking_id) {
            this.openGrowth(item.growth_tracking_id);
        } else if (item.flock_id) {
            this.openFlock(item.flock_id);
        }
    }
    
    openVaccineRecord(item) {
        // Open the flock or growth tracking record
        if (item.growth_tracking_id) {
            this.openGrowth(item.growth_tracking_id);
        } else if (item.flock_id) {
            this.openFlock(item.flock_id);
        }
    }
    
    openSlaughterRecord(item) {
        // Open the growth tracking record
        this.openGrowth(item.id);
    }

    openLocation(locationId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "poultry.location",
            res_id: locationId,
            views: [[false, "form"]],
        });
    }
}

registry.category("actions").add("poultry_dashboard", PoultryDashboard);
