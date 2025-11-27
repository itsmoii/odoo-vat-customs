/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useEffect } from "@odoo/owl";


patch(Navbar.prototype, {
    setup(){
        super.setup(...arguments);
        this.pos.proformaMode = JSON.parse(localStorage.getItem("pos_proforma_mode") || "false");
        this.pos.trainingMode = JSON.parse(localStorage.getItem("pos_training_mode") || "false");
        this.pos.advanceMode = JSON.parse(localStorage.getItem("pos_advance_mode") || "false");

        const clearModesIfRefund = () => {
            const order = this.pos.get_order?.();
            if (order?.getHasRefundLines?.()) {
                this.pos.proformaMode = false;
                this.pos.trainingMode = false;
                this.pos.advanceMode = false;
                localStorage.setItem("pos_proforma_mode", "false");
                localStorage.setItem("pos_training_mode", "false");
                localStorage.setItem("pos_advance_mode", "false");
            }
            console.log("heyyyy");
        };
        clearModesIfRefund();
        useEffect(clearModesIfRefund, () => [this.pos.get_order()]);

    },

    

    toggleProformaMode(){
        const order = this.pos.get_order?.();
        if (order?.getHasRefundLines?.()) {
            this.dialog.add(AlertDialog, {
                title: _t("Refund in progress"),
                body: _t("Cannot change modes while processing a refund order."),
            });
            return;
        }

        if(this.pos.trainingMode || this.pos.advanceMode){
            this.pos.proformaMode = false;
            localStorage.setItem("pos_proforma_mode", JSON.stringify(false));
            this.dialog.add(AlertDialog, 
                { title: _t("Mode Conflict"), 
                body: _t("You can only have one transaction mode enabled at a time.") });
            return;
        }

        this.pos.proformaMode = !this.pos.proformaMode;
        localStorage.setItem("pos_proforma_mode",
            JSON.stringify(this.pos.proformaMode));
        window.location.reload();

    },

    toggleTrainingMode(){
        const order = this.pos.get_order?.();
        if (order?.getHasRefundLines?.()) {
            this.dialog.add(AlertDialog, {
                title: _t("Refund in progress"),
                body: _t("Cannot change modes while processing a refund order."),
            });
            return;
        }

        if(this.pos.proformaMode || this.pos.advanceMode){
            this.pos.trainingMode = false;
            localStorage.setItem("pos_proforma_mode", JSON.stringify(false));
            this.dialog.add(AlertDialog, 
                { title: _t("Mode Conflict"), 
                body: _t("You can only have one transaction mode enabled at a time.") });
            return;
        }
        
        this.pos.trainingMode = !this.pos.trainingMode;
        localStorage.setItem("pos_training_mode",
            JSON.stringify(this.pos.trainingMode));
        window.location.reload();
    },

    toggleAdvanceMode(){
        const order = this.pos.get_order?.();
        if (order?.getHasRefundLines?.()) {
            this.dialog.add(AlertDialog, {
                title: _t("Refund in progress"),
                body: _t("Cannot change modes while processing a refund order."),
            });
            return;
        }

        if(this.pos.proformaMode || this.pos.trainingMode){
            this.pos.advanceMode = false;
            localStorage.setItem("pos_advance_mode", JSON.stringify(false));
            this.dialog.add(AlertDialog, 
                { title: _t("Mode Conflict"), 
                body: _t("You can only have one transaction mode enabled at a time.") });
            return;
        }
        
        this.pos.advanceMode = !this.pos.advanceMode;
        localStorage.setItem("pos_advance_mode",
            JSON.stringify(this.pos.advanceMode));
        window.location.reload();
    },

});