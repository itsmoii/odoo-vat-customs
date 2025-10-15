from odoo import models, fields, api
from datetime import datetime, timedelta


FINAL_STATES = ['paid', 'done', 'invoiced']


class FinanceSalesDetails(models.TransientModel):
    _name = 'finance.sales.details'
    _description = 'Finance Sales Details'

    date_from = fields.Date(string='From', default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string='To', default=lambda self: fields.Date.context_today(self))

    total_sales = fields.Float(string='Total Sales', compute='_compute_metrics')
    total_vat = fields.Float(string='Total VAT', compute='_compute_metrics')
    orders_count = fields.Integer(string='# Orders', compute='_compute_metrics')
    avg_basket = fields.Float(string='Avg Basket', compute='_compute_metrics')

    payments_split_html = fields.Html(string='Payments Split', compute='_compute_widgets')
    trend_html = fields.Html(string='Sales & VAT Trend', compute='_compute_widgets')
    top_sellers_html = fields.Html(string='Top Sellers', compute='_compute_widgets')

    def _dt_bounds(self):
        self.ensure_one()
        # Use user/company timezone boundaries
        tz_now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        df = self.date_from or fields.Date.context_today(self)
        dt = self.date_to or df
        start = datetime.combine(df, datetime.min.time())
        end = datetime.combine(dt, datetime.max.time())
        # Convert to server strings
        return fields.Datetime.to_string(start), fields.Datetime.to_string(end)

    @api.depends('date_from', 'date_to')
    def _compute_metrics(self):
        for w in self:
            start, end = w._dt_bounds()
            Order = w.env['pos.order']
            domain = [('state', 'in', FINAL_STATES), ('date_order', '>=', start), ('date_order', '<=', end)]
            data = Order.read_group(domain, ['amount_total:sum', 'amount_tax:sum', 'id:count'], [])
            if data:
                w.total_sales = data[0].get('amount_total_sum', 0.0)
                w.total_vat = data[0].get('amount_tax_sum', 0.0)
                w.orders_count = int(data[0].get('id_count', 0))
            else:
                w.total_sales = w.total_vat = 0.0
                w.orders_count = 0
            w.avg_basket = (w.total_sales / w.orders_count) if w.orders_count else 0.0

    @api.depends('date_from', 'date_to')
    def _compute_widgets(self):
        for w in self:
            start, end = w._dt_bounds()
            # Payments split
            pay_rg = w.env['pos.payment'].read_group(
                [('pos_order_id.state', 'in', FINAL_STATES), ('pos_order_id.date_order', '>=', start), ('pos_order_id.date_order', '<=', end)],
                ['amount:sum', 'payment_method_id'], ['payment_method_id']
            )
            total_p = sum(p.get('amount', 0.0) for p in pay_rg) or 1.0
            rows = []
            for r in pay_rg:
                name = r['payment_method_id'][1]
                amt = r.get('amount', 0.0)
                pct = (amt / total_p) * 100.0
                rows.append(f"<tr><td>{name}</td><td style='text-align:right'>${amt:,.2f}</td><td style='text-align:right'>{pct:.1f}%</td></tr>")
            w.payments_split_html = (
                "<div><h4>Payments Split</h4><table class='o_list_view' style='width:100%'><thead><tr>"
                "<th>Method</th><th>Amount</th><th>%</th></tr></thead>"
                f"<tbody>{''.join(rows) or '<tr><td colspan=3>No payments</td></tr>'}</tbody></table></div>"
            )

            # Trend by day
            ord_rg = w.env['pos.order'].read_group(
                [('state', 'in', FINAL_STATES), ('date_order', '>=', start), ('date_order', '<=', end)],
                ['amount_total:sum', 'amount_tax:sum'], ['date_order:day']
            )
            ord_rg.sort(key=lambda r: r['date_order'] or '')
            rows2 = []
            for r in ord_rg:
                day = r.get('date_order:day') or r.get('date_order')
                amt = r.get('amount_total_sum', 0.0)
                vat = r.get('amount_tax_sum', 0.0)
                rows2.append(f"<tr><td>{day}</td><td style='text-align:right'>${amt:,.2f}</td><td style='text-align:right'>${vat:,.2f}</td></tr>")
            w.trend_html = (
                "<div><h4>Sales &amp; VAT Trend</h4><table class='o_list_view' style='width:100%'>"
                "<thead><tr><th>Date</th><th>Sales</th><th>VAT</th></tr></thead>"
                f"<tbody>{''.join(rows2) or '<tr><td colspan=3>No data</td></tr>'}</tbody></table></div>"
            )

            # Top sellers by quantity
            line_rg = w.env['pos.order.line'].read_group(
                [('order_id.state', 'in', FINAL_STATES), ('order_id.date_order', '>=', start), ('order_id.date_order', '<=', end)],
                ['qty:sum', 'price_subtotal_incl:sum', 'product_id'], ['product_id'], limit=10, orderby='qty desc'
            )
            items = []
            for r in line_rg:
                name = r['product_id'][1]
                qty = r.get('qty', 0.0)
                rev = r.get('price_subtotal_incl_sum', 0.0)
                items.append(f"<tr><td>{name}</td><td style='text-align:right'>{qty:,.0f}</td><td style='text-align:right'>${rev:,.2f}</td></tr>")
            w.top_sellers_html = (
                "<div><h4>Top Sellers</h4><table class='o_list_view' style='width:100%'>"
                "<thead><tr><th>Product</th><th>Qty</th><th>Revenue</th></tr></thead>"
                f"<tbody>{''.join(items) or '<tr><td colspan=3>No items</td></tr>'}</tbody></table></div>"
            )

    def action_open_orders(self):
        self.ensure_one()
        start, end = self._dt_bounds()
        action = self.env.ref('finance_core.action_finance_sales_details').read()[0]
        action['domain'] = [
            ('state', 'in', FINAL_STATES),
            ('date_order', '>=', start),
            ('date_order', '<=', end),
        ]
        return action
