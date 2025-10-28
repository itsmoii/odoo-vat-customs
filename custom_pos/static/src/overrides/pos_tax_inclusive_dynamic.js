/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

/**
 * Dynamic Fiji VAT (12.5%) tax-inclusive UI patch.
 *
 * - Computes a tax-inclusive unit price from the base price and a fixed VAT rate
 *   when an explicit tax-inclusive field is not present.
 * - Displays tax-inclusive values on product tiles (via PosStore.getProductPrice)
 *   and on the orderline (cart) header.
 *
 * Note: This only affects the UI. Backend journal/tax computation remains
 * driven by the POS tax engine.
 */

const VAT_RATE = 0.125; // 12.5%

// [1] POS STORE: return tax-inclusive unit price
patch(PosStore.prototype, "custom_pos.tax_inclusive_dynamic.store", {
    getProductPrice(product, pricelist) {
        try {
            // Prefer existing inclusive fields if present
            const incl = product.x_total_price ?? product.x_price_incl_tax;
            if (typeof incl === "number" && incl > 0) {
                return incl;
            }
            // Fallback: compute from base (list_price or other custom base)
            const base =
                product.list_price ??
                product.x_selling_price ??
                product.standard_price ??
                0;
            return base * (1 + VAT_RATE);
        } catch (err) {
            console.error("[custom_pos] tax_inclusive_dynamic getProductPrice error", err);
            return product.list_price || 0;
        }
    },
});

// [2] ORDERLINE: show tax-inclusive total for the line
patch(PosOrderline.prototype, "custom_pos.tax_inclusive_dynamic.orderline", {
    get_display_price() {
        // compute tax-inclusive per-unit then multiply by quantity
        const product = this.get_product();
        const base =
            product.list_price ??
            product.x_selling_price ??
            product.standard_price ??
            0;
        const unitIncl = (product.x_total_price ?? product.x_price_incl_tax ?? base * (1 + VAT_RATE));
        return unitIncl * this.get_quantity();
    },
    getPriceString() {
        return formatCurrency(this.get_display_price(), this.currency);
    },
});

console.log("✅ [custom_pos] Dynamic tax-inclusive price (12.5%) fully active.");

