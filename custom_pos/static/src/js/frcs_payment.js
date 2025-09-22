/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { useListener } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";

console.log('%c[pos_taxcore_bridge] JS file loaded', 'color:lime;font-weight:bold;');

function taxcoreResponse(expectedOrigin, timeoutMs = 15000) {
    return new promise((resolve, reject) => {

        const timer = setTimeout(() => {
            window.removeEventListener("message", onMsg);
            reject(new Error("Taxcore Response timeout"));

        }, timeoutMs);

        function onMsg(ev) {
            try{

                if (expectedOrigin && ev.origin !== expectedOrigin){
                    return;
                }

                if (payload && payload.response){
                    clearTimeout(timer);
                    window.removeEventListener("message", onMsg);
                    resolve(payload.response);
                }

            }catch (e){

            }
        }
        
        window.addEventListener("message", onMsg, false);
    });
}