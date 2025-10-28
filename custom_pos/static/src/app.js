/** @odoo-module **/

import { registry } from "@web/core/registry";
import { PosStore } from "@point_of_sale/app/store/pos_store";

// ✅ Patch to expose POS service globally for browser console debugging
export const exposePosDebug = () => {
    try {
        window.odoo = window.odoo || {};
        window.odoo.DEBUG = window.odoo.DEBUG || {};
        window.odoo.DEBUG.services = window.odoo.DEBUG.services || {};

        const services = registry.category("services");
        const posService = services.get("pos");
        if (posService) {
            window.odoo.DEBUG.services.pos = posService;
            console.log("✅ POS debug service successfully exposed:", posService);
        } else {
            console.warn("⚠️ POS service not available yet, retrying...");
            setTimeout(exposePosDebug, 2000);
        }
    } catch (err) {
        console.error("❌ Failed to expose POS debug service:", err);
    }
};

// Call immediately
exposePosDebug();
