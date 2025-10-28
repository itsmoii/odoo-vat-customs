/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";
import { _t } from "@web/core/l10n/translation";

// Always compute product price as tax-included for display on the product grid
patch(PosStore.prototype, "custom_pos.vat_inclusive_product_price", {
    getProductPrice(product, p = false) {
        // 1) Prefer custom inclusive field when present
        const totalField =
            product.x_total_price ?? product.x_price_incl_tax;
        if (typeof totalField === "number" && totalField > 0) {
            return totalField;
        }
        // 2) Fallback to robust tax-included computation using POS tax engine
        const taxesData = this.getProducePriceDetails(product, p);
        return taxesData.total_included;
    },
});

// Make orderline unit prices and totals tax-included regardless of POS config
patch(PosOrderline.prototype, "custom_pos.vat_inclusive_orderline", {
    get_unit_display_price() {
        return this.get_all_prices(1).priceWithTax;
    },
    getUnitDisplayPriceBeforeDiscount() {
        return this.get_all_prices(1).priceWithTaxBeforeDiscount;
    },
    get_display_price() {
        return this.get_price_with_tax();
    },
    getPriceString() {
        // Keep original semantics for 'Free' and combo parents
        if (this.get_discount_str() === "100") {
            return _t("Free");
        }
        if (this.combo_line_ids?.length > 0) {
            return "";
        }
        // Force tax-included formatted value
        return formatCurrency(this.get_price_with_tax(), this.currency);
    },
});

// Ensure UI data object also reflects tax-included price on the right of the line
const _superGetDisplayData = PosOrderline.prototype.getDisplayData;
patch(PosOrderline.prototype, "custom_pos.vat_inclusive_orderline_displaydata", {
    getDisplayData() {
        const data = _superGetDisplayData.apply(this, arguments);
        if (this.get_discount_str() === "100") {
            data.price = _t("Free");
        } else if (this.combo_line_ids?.length > 0) {
            data.price = "";
        } else {
            data.price = formatCurrency(this.get_price_with_tax(), this.currency);
        }
        return data;
    },
});

// Tiny log to verify the patch is active in browser console
console.info("custom_pos: VAT-inclusive price patch active");
