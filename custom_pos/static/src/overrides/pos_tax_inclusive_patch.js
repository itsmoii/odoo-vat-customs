/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { _t } from "@web/core/l10n/translation";

/**
 * Force POS to use and display tax-inclusive prices.
 * - Prefer inventory's inclusive fields when present
 * - Otherwise fallback to POS tax engine total_included
 */

console.log("\u{1F4A1} [custom_pos] Tax-Inclusive Price Patch Loaded");

patch(PosStore.prototype, "custom_pos.tax_inclusive_prices.final", {
    // Keep the same signature as core: getProductPrice(product, p = false)
    getProductPrice(product, p = false) {
        try {
            // 1) Prefer inclusive field(s) from inventory if available
            const total = product.x_total_price ?? product.x_price_incl_tax;
            if (typeof total === "number" && total > 0) {
                return total;
            }

            // 2) Fallback to robust tax-included computation using POS engine
            const details = this.getProducePriceDetails(product, p);
            return details.total_included;
        } catch (err) {
            console.error("[custom_pos] getProductPrice error:", err);
            return product.list_price;
        }
    },
});

patch(PosOrderline.prototype, "custom_pos.tax_inclusive_orderline.final", {
    get_display_price() {
        return this.get_price_with_tax();
    },
    getPriceString() {
        // Preserve original semantics for Free and combo parent lines
        if (this.get_discount_str() === "100") {
            return _t("Free");
        }
        if (this.combo_line_ids?.length > 0) {
            return "";
        }
        return formatCurrency(this.get_display_price(), this.currency);
    },
});

console.log("\u2705 POS is now displaying Tax-Inclusive prices everywhere!");

