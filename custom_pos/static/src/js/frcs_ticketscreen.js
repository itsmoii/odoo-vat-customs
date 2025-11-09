import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { sendToTaxcore } from "./frcs_service";


patch (TicketScreen.prototype, {

    getCashier(order) {
        return order.user_id?.name;
    },

    async onReprint() {
        const order = this.getSelectedOrder();
        const isRefund = order?.getHasRefundLines?.() || false;

        console.log("COPY RFUNNDDDDD" + isRefund);

        if (!order) {
            this.notification.add(
                this.env._t("Select an order first"), 
                { type: "warning" }
            );

            return;
        }

        //Prepare payload to send to TaxCore
        const invoiceId = await this.pos.data.call (
            "pos.order.fiscal.record",
            "get_invoice_number",
            [order.id]
        );

        const referentDocumentDT = await this.pos.data.call (
            "pos.order.fiscal.record",
            "get_created_time",
            [order.id]
        );

        if (!invoiceId) {
            this.notification.add (
                this.env._t("No stored fiscal payload for this order"),
                {type: danger}
            );

            return;
        }

        const sdcInvoice = await this.pos.data.call (
            "pos.order.fiscal.record",
            "get_sdc_invoice",
            [order.id]
        )


        let invoicePayload;

        const items = order.get_orderlines().map((line) => ({
            GTIN: line.product?.barcode || null,
            Name: line.get_full_product_name() || "Item",
            Quantity: Math.abs(line.get_quantity()),
            Discount: line.get_discount(),
            Labels: line.product?.taxes_id?.map((tax) => tax.name).filter(Boolean) || ["G"],
            TotalAmount: Math.abs(line.get_price_with_tax()),
        }));

        
        let transactionType;

        if (isRefund){
            transactionType = "Refund";
        } else {
            transactionType = "Sale";
        }




        try{

            invoicePayload = {
                DateAndTimeOfIssue: new Date().toISOString(),
                Cashier: this.pos.get_cashier().name,
                BD: null,
                BuyerCostCenterId: null,
                IT:"Copy",
                TT: transactionType,
                paymentType: "Cash",
                //payment: paymentTypes,
                InvoiceNumber: "22222",
                ReferentDocumentNumber: sdcInvoice,
                ReferentDocumentDT: referentDocumentDT,
                PAC: "3AYVNZ",
                Options: {
                    OmitTextualRepresentation: 0,
                    OmitQRCodeGen: 0,
                },
                Items: items,
            };

        } catch (err) {
            console.error("Taxcore validation failed: ", err);
        } 

        const response = await sendToTaxcore({ pos: this.pos, payload:invoicePayload });
        order.setTaxCoreResponse(response);

        if (this.pos.get_order().uuid !== order.uuid) {
            this.pos.set_order(order);
        }

        this.pos.showScreen("ReceiptScreen");


    
    },

    getOrderInvoiceLabel(order){

        const invoiceLabel = this.pos.data.call (
            "pos.order.fiscal.record",
            "get_invoice_label",
            [order.id]
        );

        if (!invoiceLabel) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Invoice Label"),
                body: _t("No invoice label found for this order Id"),
                confirmLabel: _t("OK"),
            })

            return;
        }

        return invoiceLabel;

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