/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { sendToTaxcore } from "./frcs_service";
import { _t } from "@web/core/l10n/translation";


const DEFAULT_LABEL = ["A"];


// Sending data to TaxCore
patch(PaymentScreen.prototype, {

    async onMounted(){
        await super.onMounted?.();

        if (this.pos.proformaMode) {
            await this._ensureProformaLine();
        }

        if (this.pos.trainingMode){
            await this._ensureTrainingLine();
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

    async _ensureTrainingLine(){
        const order = this.currentOrder;
        if (!order) return;

        order.setIsTraining?.(true);

        const pm = this.pos.models["pos.payment.method"].find((m) =>
        m.name === "Training");

        if (!pm){
            this.notification.add(
                _t('Create a payment method named "Training" and add it to the POS config.'),
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

        if (this.pos.trainingMode) {
            await this._ensureTrainingLine();
            this.currentOrder.setIsTraining(true);
        }

        return await super.validateOrder(isForce);
    },
    
    async _finalizeValidation() {
        const order = this.currentOrder;
        if (!order) {
            return super._finalizeValidation(...arguments);
        }

        const hasRefundLines = order.getHasRefundLines();
        const isRefund = hasRefundLines;
        console.log("OVERRRR HEREEEE:" + isRefund);

        const isAdvance = this.pos.advanceMode || order.isAdvance?.();
        const isProforma = this.pos.proformaMode || order.isProforma?.();
        const isTraining = this.pos.trainingMode || order.isTraining?.();


        const invoiceInput = document.getElementById("invoiceInput");
        const invoiceOutput = document.getElementById("invoiceOutput");
        const taxcoreButton = document.getElementById("taxcore_sign_element");
        if (!invoiceInput || !invoiceOutput || !taxcoreButton) {
            console.warn("TaxCore input/output elements missing");
            return result;
        }

        const invoiceType = ["Normal", "Refund", "Copy", "Training", "Proforma", "Advance"];
        const transactionType = ["Sale", "Refund"];
        let transaction_type;
        let invoice_type;

        if (isRefund){
            invoice_type = invoiceType[0];
            transaction_type = transactionType[1];
        } else if (isAdvance){
            invoice_type = invoiceType[5];
            transaction_type = transactionType[0];
        }else if(isProforma){
            invoice_type = invoiceType[4];
            transaction_type = transactionType[0];
        } else if(isTraining){
            invoice_type = invoiceType[3];
            transaction_type = transactionType[0];
        }else {
            invoice_type = invoiceType[0];
            transaction_type = transactionType[0];
        }

        const items = order.get_orderlines().map((line) => {
            const labels =
                line.product?.taxes_id?.map((tax) => tax.name).filter(Boolean) || [];
            if (!labels.length) {
                labels.push(...DEFAULT_LABEL);
            }
            
            let quantity = line.get_quantity()
            
            const discount = line.get_discount();
            console.log("DISCOUNTTTTT:" + discount);

            if (transaction_type == transactionType[1]){
                quantity = Math.abs(line.get_quantity());
            }

            return {
                
                GTIN: line.product?.barcode || null,
                Name: line.get_full_product_name() || "Item",
                Quantity: quantity,
                Discount: discount,
                Labels: labels,
                unitPrice: line.get_price_with_tax(),
                TotalAmount: Math.abs(line.get_price_with_tax()),
            };
        });

        const paymentTypes = order.payment_ids.map((line)=> {
            let type = line.payment_method_id.type;
            if(type == "cash"){
                type ="Cash";
            }else if (type == "bank"){
                type = "Card";
            }

            return {
                Amount: line.get_amount(),
                PaymentType: type,

            };
        });

        console.log("PAYMENNNNTTT TYYYYYPPPESSS", paymentTypes);

        const invoice_num = "31082017-99";

        const spinnerEl = document.getElementById("taxcore-loading");
        if(spinnerEl) spinnerEl.classList.remove("d-none");

        let invoicePayload;

        try{

            invoicePayload = {
                DateAndTimeOfIssue: new Date().toISOString(),
                Cashier: this.pos.get_cashier().name,
                BD: null,
                BuyerCostCenterId: null,
                IT:invoice_type,
                TT: transaction_type,
                paymentType: "Cash",
                //payment: paymentTypes,
                InvoiceNumber: invoice_num,
                ReferentDocumentNumber: "",
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

        const taxcoreResponse = await sendToTaxcore({pos: this.pos, payload: invoicePayload });
        const invoice_label = taxcoreResponse.InvoiceCounterExtension;
        const journal = taxcoreResponse;

        order.setTaxCoreResponse(taxcoreResponse);
        order.setInvoiceNumber(invoice_num);
        order.setSDCInvoice(taxcoreResponse.IN);
        order.setInvoiceLabel(invoice_label);

        const result = await super._finalizeValidation(...arguments); 

        let backendId = typeof order.id === "number" ? order.id : undefined;
        if (!backendId) {
            await this.pos.data.syncData();
            backendId = typeof order.id === "number" ? order.id : undefined;
        }
        if (!backendId) {
            console.warn("No backend order id yet; skipping print job");
            return result;
        }
        
            

        if (journal) {
            await this.pos.data.execute({
                type: "write",
                model: "pos.order",
                ids: [backendId],
                values: { taxcore_journal: JSON.stringify(journal) },
            });


            // await this.pos.data.call(
            //     "pos.order",
            //     "action_pos_order_paid",
            //     [backendId]
            // );

            // await this.pos.data.call(
            //     "pos.print.job",
            //     "cron_process_jobs",
            //     []
            // );
        
            
        }
        return result;
    },
});

patch(PosOrder.prototype, {
    //Display TaxCore response on POS receipt
    export_for_printing() {
        const data = super.export_for_printing(...arguments);
        if (this.taxcore_response && this.taxcore_response.status_code !== 400 && this.taxcore_response.Journal) {

            const journalLines = this.taxcore_response.Journal.split('\r\n');
            const endLine = journalLines[journalLines.length - 2];
            const beforeEnd = journalLines.slice(0,-2).map((line,i)=>({
                text:line,
                idx:i
            }));


            data.taxcore_response = {

                ...this.taxcore_response,
                journal_before_end:beforeEnd,
                journal_end_line:endLine,

            };
        }
        return data;
    },
    //method to store TaxCore response
    setTaxCoreResponse(payload){
        this.taxcore_payload = payload;
        this.taxcore_response = payload;

    },

    setInvoiceNumber(invNum){
        this.invoice_number = invNum;
    },

    setSDCInvoice(SDCInv){
        this.sdc_invoice = SDCInv;
    },

    setInvoiceLabel(invLabel){
        this.invoice_label = invLabel;
    },

    setup(vals) {
        super.setup(vals);
        this.taxcore_payload = vals.taxcore_payload || null;
        this.invoice_number = vals.invoice_number || null;
        this.sdc_invoice = vals.sdc_invoice || null;
        this.invoice_label = vals.invoice_label || null;

    },

    //Sends TaxCore response to the backend DB 
    serialize(){
        const data = super.serialize(...arguments);
        if(this.taxcore_payload){
            data.taxcore_payload = this.taxcore_payload;
        }
        if(this.invoice_number){
            data.invoice_number = this.invoice_number;
        }
        if(this.sdc_invoice){
            data.sdc_invoice = this.sdc_invoice;
        }
        if(this.invoice_label){
            data.invoice_label = this.invoice_label;
        }
        data.is_proforma = !!this.is_proforma;

        return data;
    },
    
});



