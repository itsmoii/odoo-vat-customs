/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Navbar } from "@point_of_sale/app/navbar/navbar";

patch(Navbar.prototype, {
    setup(){
        super.setup(...arguments);
        this.pos.proformaMode = JSON.parse(localStorage.getItem("pos_proforma_mode") || "false");
    },

    toggleProformaMode(){
        this.pos.proformaMode = !this.pos.proformaMode;
        localStorage.setItem("pos_proforma_mode",
            JSON.stringify(this.pos.proformaMode));
        window.location.reload();

    },
});