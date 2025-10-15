/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// Capture original getter so we can delegate when a category is selected
const superProductsToDisplay = Object.getOwnPropertyDescriptor(
    ProductScreen.prototype,
    "productsToDisplay"
)?.get;

patch(ProductScreen.prototype, {
    setup() {
        this._super && this._super(...arguments);
        // Do not pre-select any category on load; start with empty list until user clicks a category
        // ProductScreen already shows all products when no category is selected; we will block that in the getter below
    },

    get productsToDisplay() {
        // When no search and no selected category, show nothing to encourage category-first workflow
        if (!this.pos.selectedCategory?.id && this.searchWord === "") {
            return [];
        }
        // Fallback to native behavior otherwise (search or category selected)
        return superProductsToDisplay ? superProductsToDisplay.call(this) : [];
    },
});

