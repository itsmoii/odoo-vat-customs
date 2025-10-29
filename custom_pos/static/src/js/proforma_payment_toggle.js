/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";


patch(PaymentScreen.prototype, {
    async onMounted(){
        await super.onMounted?.();

        if (this.pos.proformaMode) {
            await this._ensureProformaLine();
        }
    },
    
    async _ensureProformaLine(){
        const order = this.currentOrder;
        if (!order) return;

        order.setIsProforma?.(true);

        const pm = this.pos.models["pos.payment.method"].find((m) =>
        m.name === "Proforma");

        if (!pm){
            this.notification.add(
                _t('Create a payment method named "Proforma" and add it to the POS config.'),
                { type: "warning"});

            return;
        }

        // Remove previous Proforma line
        for (const line of order.paymentlines || []) {
            if (line.payment_method?.id === pm.id) {
                order.remove_paymentline(line);
            }
        }

        // Add a line that equals current due
        const added = await this.addNewPaymentLine(pm);
        if (added) {
            const lines = order.paymentlines || [];
            const lastline = lines [lines.length -1];
            if(lastline){
                lastline.set_amount(order.get_total_with_tax() - order.get_rounding_applied());
            }
        }
    },

    async validateOrder(isForce) {
        if (this.pos.proformaMode) {
            await this._ensureProformaLine();
            this.currentOrder.setIsProforma(true);
        }

        return await super.validateOrder(isForce);
    },

});