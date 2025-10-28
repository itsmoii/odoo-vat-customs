import { patch } from "@web/core/utils/patch";
import { ProductProduct } from "@point_of_sale/app/models/product_product";

const _superGetPrice = ProductProduct.prototype.get_price;

patch(ProductProduct.prototype, "custom_pos.use_inventory_total_price", {
    get_price(pricelist, quantity, price_extra = 0, recurring = false, list_price = false) {
        try {
            // Accept multiple possible custom field names coming from backend
            const totalIncl =
                this.x_total_price ?? this.x_price_incl_tax;
            if (totalIncl !== undefined && totalIncl !== null) {
                // Compute a net price that will yield the inclusive value as tax-included unit price
                let percentRate = 0.0;
                const taxes = this.taxes_id || [];
                // Only handle percent taxes; if other types are present, fall back to default behavior
                for (const tax of taxes) {
                    if (tax.amount_type === "percent") {
                        percentRate += (tax.amount || 0) / 100.0;
                    } else if (tax.amount_type !== "percent" && tax.amount) {
                        return _superGetPrice.apply(this, arguments);
                    }
                }
                const dp =
                    this.models["decimal.precision"].find((d) => d.name === "Product Price")?.digits || 2;
                const net = percentRate ? totalIncl / (1 + percentRate) : totalIncl;
                const price = (net || 0) + (price_extra || 0);
                return window.parseFloat((price || 0).toFixed(dp));
            }
        } catch (e) {
            // ignore and fall back
        }
        return _superGetPrice.apply(this, arguments);
    },
});
