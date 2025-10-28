/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { _t } from "@web/core/l10n/translation";

/**
 * Tax-Inclusive Price Display — Inventory “Total Price” driven.
 * Works on Odoo 18 POS (OWL).
 *
 * Strategy:
 *  - Patch PosStore.getProductPrice to prefer the inclusive field coming from inventory
 *    (x_total_price or x_price_incl_tax). Otherwise, fall back to the POS tax engine
 *    and use total_included from getProducePriceDetails.
 *  - Patch PosOrderline to show tax-included amounts in the cart.
 *    (Product tiles already call PosStore.getProductPrice under the hood.)
 */

console.log("💡 [custom_pos] Tax-Inclusive Price Patch (Full) Loaded");

patch(PosStore.prototype, "custom_pos.tax_inclusive_full.store", {
    getProductPrice(product, p = false) {
        try {
            // Prefer inclusive fields from inventory if present
            const total = product.x_total_price ?? product.x_price_incl_tax;
            if (typeof total === "number" && total > 0) {
                return total;
            }
            // Robust fallback to POS tax engine
            const details = this.getProducePriceDetails(product, p);
            return details.total_included;
        } catch (err) {
            console.error("[custom_pos] getProductPrice error:", err);
            return product.list_price;
        }
    },
});

patch(PosOrderline.prototype, "custom_pos.tax_inclusive_full.orderline", {
    get_display_price() {
        return this.get_price_with_tax();
    },
    getPriceString() {
        if (this.get_discount_str() === "100") {
            return _t("Free");
        }
        if (this.combo_line_ids?.length > 0) {
            return "";
        }
        return formatCurrency(this.get_display_price(), this.currency);
    },
});

console.log("✅ POS now shows Tax-Inclusive prices (tiles, cart, totals)");

