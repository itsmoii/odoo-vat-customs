import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";


patch (TicketScreen.prototype, {

    getCashier(order) {
        return order.user_id?.name;
    },

    _getReplicaDetails(partner, order){
        return Object.values(this.pos.getLinesToRefund).filter(
            (duplicate) =>
                !this.pos.isProductQtyZero(duplicate.qty) &&
                duplicate.line.order_id.uuid === order.uuid &&
                (partner ? duplicate.line.order_id.partner_id?.id === partner.id : true) &&
                !duplicate.destination_order_id
        )

    },

    async onReprint() {
        const order = this.getSelectedOrder();

        if (!order) {
            this.notification.add(
                this.env._t("Select an order first"), 
                { type: "warning" }
            );

            return;
        }

        //Prepare payload to send to TaxCore
        const invoiceId = await this.rpc ({
            model: "pos.order.fiscal.record",
            method: "get_invoice_number",
            args: [order.id],
        })

        if (!invoiceId) {
            this.notification.add (
                this.env._t("No stored fiscal payload for this order"),
                {type: danger}
            );

            return;
        }


    
    },

});

patch (ActionpadWidget.prototype, {

    setup(){
        super.setup(...arguments);
        this.secondaryActionEnabled = typeof this.props.secondaryActionToTrigger === "function";
    },

});

patch(ActionpadWidget, {
    props: {
        ...ActionpadWidget.props,
        secondaryActionName: { type: String, optional: true},
        secondaryActionToTrigger: {type: Function, optional: true},
    },
});