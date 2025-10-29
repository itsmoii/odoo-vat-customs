/** @odoo-module **/

import { loadJS } from "@web/core/assets";

const TAXCORE_URL = "https://vsdc.sandbox.taxcore.online/onlinepos/v1/taxcore.min.js";

async function waitForTaxCoreIframe() {
    let iframe =document.getElementById("taxcore");
    for (let tries = 0; tries < 30 && !iframe; tries++) {
        await new Promise((resolve) => setTimeout(resolve, 100));
        iframe = document.getElementById("taxCore");
    }
    if (!iframe) {
        throw new Error("TaxCore iframe is missing from the DOM.");
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
        await new Promise((resolve) => setTimeout(resolve, 200));
    }
    return iframe;
}

export async function sendToTaxcore({
    pos,
    payload,
    invoiceInputElementId = "invoiceInput",
    invoiceOutputElementId = "invoiceOutput",
    signButtonId = "taxcore_sign_element",
    spinnerElementId = "taxcore-loading",
}) {
    await loadJS(TAXCORE_URL);
    await waitForTaxCoreIframe();

    const invoiceInput = document.getElementById(invoiceInputElementId);
    const invoiceOutput = document.getElementById(invoiceOutputElementId);
    const signButton = document.getElementById(signButtonId);
    const spinnerEl = spinnerElementId && document.getElementById(spinnerElementId);

    if (!invoiceInput || !invoiceOutput || !signButton) {
        throw new Error("TaxCore input/output/sign elements are missing.");
    }

    if (spinnerEl) {
        spinnerEl.classList.remove("d-none");
    }

    invoiceInput.value = JSON.stringify(payload, null, 4);
    invoiceOutput.value = "";

    return await new Promise((resolve, reject) => {
        const handler = (event) => {
            try {
                const payload = JSON.parse(event.data);
                const response = payload.response || payload;
                invoiceOutput.value = JSON.stringify(response, null, 4);
                resolve(response || payload.response);
            } catch (error) {
                reject(new Error(`Invalid TaxCore response: ${event.data}`));
            } finally {
                window.removeEventListener("message", handler);
                spinnerEl?.classList.add("d-none");
            }
        };

        window.addEventListener("message", handler);
        signButton.click();
    });
}