/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

const TAXCORE_URL = "https://vsdc.sandbox.taxcore.online/onlinepos/v1/taxcore.min.js";
const DEFAULT_LABEL = ["A"];

function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForTaxCoreIframe() {
    let iframe = document.getElementById("taxCore");
    for (let tries = 0; tries < 30 && !iframe; tries++) {
        await sleep(100);
        iframe = document.getElementById("taxCore");
    }
    if (!iframe) {
        console.warn("TaxCore iframe missing");
        return null;
    }
    if (!iframe.dataset.loaded) {
        await new Promise((resolve) => {
            const done = () => {
                iframe.dataset.loaded = "true";
                iframe.removeEventListener("load", done);
                resolve();
            };
            iframe.addEventListener("load", done, { once: true });
        });
        await sleep(200);
    }
    return iframe;
}

// Sending data to TaxCore
patch(PaymentScreen.prototype, {
    async _finalizeValidation() {
        const order = this.currentOrder;
        if (!order) {
            return super._finalizeValidation(...arguments);
        }

        const hasRefundLines = order.getHasRefundLines();
        const isRefund = hasRefundLines;
        console.log("OVERRRR HEREEEE:" + isRefund);


        const invoiceInput = document.getElementById("invoiceInput");
        const invoiceOutput = document.getElementById("invoiceOutput");
        const taxcoreButton = document.getElementById("taxcore_sign_element");
        if (!invoiceInput || !invoiceOutput || !taxcoreButton) {
            console.warn("TaxCore input/output elements missing");
            return result;
        }

        const transactionType = ["Sale", "Refund", "Copy", "Training", "Proforma"];
        let transaction_type;

        if (isRefund){
            transaction_type = transactionType[1];
        } else {
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

            await loadJS(TAXCORE_URL);
            await waitForTaxCoreIframe();

            invoicePayload = {
                DateAndTimeOfIssue: new Date().toISOString(),
                Cashier: this.pos.get_cashier().name,
                BD: null,
                BuyerCostCenterId: null,
                IT:"Normal",
                TT: transaction_type,
                paymentType: "Cash",
                //payment: paymentTypes,
                InvoiceNumber: invoice_num,
                ReferentDocumentNumber: "9A2PAXC4-XLNZ9VO0-70",
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
        
        

        invoiceInput.value = JSON.stringify(invoicePayload, null, 4);
        invoiceOutput.value = "";

        //TaxCore Response
        // window.onmessage = (event) => {
        //     try {
        //         const payload = JSON.parse(event.data);
        //         const response = payload.response || payload;
        //         invoiceOutput.value = JSON.stringify(response, null, 4);
        //         order.taxcore_response = response;
        //         order.setTaxCoreResponse(response);
        //     } catch (err) {
        //         console.error("Invalid TaxCore response:", err, event.data);
        //     } finally {
        //         spinnerEl.classList.add("d-none");
        //     }
        // };

        // taxcoreButton.click();
        // return await result;
        const  taxcoreResponse = await new Promise((resolve, reject) => {
            const handler = (event) => {
                try{
                    const payload = JSON.parse(event.data);
                    const response = payload.response || payload; 
                    invoiceOutput.value = JSON.stringify(response, null, 4);
                    order.taxcore_response = response;
                    resolve(payload.response || payload);
                } catch (err) {
                    console.error("Invalid TaxCore response:", err, event.data);
                }finally {
                    window.removeEventListener("message", handler);
                    spinnerEl.classList.add("d-none");
                }
            };
            window.addEventListener("message", handler);
            taxcoreButton.click();
        });

        order.setTaxCoreResponse(taxcoreResponse);
        order.setInvoiceNumber(invoice_num);



        return super._finalizeValidation(...arguments);


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

    },

    setInvoiceNumber(invNum){
        this.invoice_number = invNum;
    },

    setup(vals) {
        super.setup(vals);
        this.taxcore_payload = vals.taxcore_payload || null;
        this.invoice_number = vals.invoice_number || null;

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

        return data;
    },
    
});

