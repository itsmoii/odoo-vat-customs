/**
 * Add per-unit Tax (FJ$) and Total (FJ$) to the Orderline display data,
 * so we can show them in the POS order widget UI via QWeb patch.
 */
import { patch } from "@web/core/utils/patch";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

const _superGetDisplayData = PosOrderline.prototype.getDisplayData;

patch(PosOrderline.prototype, "custom_pos.orderline_total_price", {
    getDisplayData() {
        const data = _superGetDisplayData.apply(this, arguments);
        try {
            // Per-unit prices (qty=1) to match the UI that shows unit price
            const perUnit = this.get_all_prices(1);
            const unitTax = perUnit?.tax || 0.0;
            const unitTotal = perUnit?.priceWithTax || 0.0;
            return {
                ...data,
                unitTax: formatCurrency(unitTax, this.currency),
                unitTotal: formatCurrency(unitTotal, this.currency),
            };
        } catch (e) {
            // Fallback safely to original data if anything goes wrong
            return data;
        }
    },
});

