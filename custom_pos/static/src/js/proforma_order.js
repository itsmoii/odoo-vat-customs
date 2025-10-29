/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {
    setup(vals){
        super.setup(vals);
        this.is_proforma = vals.is_proforma || false;
    },

    setIsProforma(v){
        this.is_proforma = !!v;
    },

    isProforma(){
        return !!this.is_proforma;
    },
});