/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";

// Adds a tax-included display price under the product name on tiles.
// Relies on the PosStore.getProductPrice[Formatted] already patched to be tax-included.
patch(ProductCard.prototype, "custom_pos.product_card_price", {
    get tileDisplayPrice() {
        try {
            const pos = this.env.services.pos;
            // Prefer formatted helper to respect currency and /uom for weight products.
            return pos.getProductPriceFormatted(this.props.product);
        } catch (e) {
            return "";
        }
    },
});

