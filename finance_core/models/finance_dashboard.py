from odoo import models, fields, api
from datetime import date, timedelta, datetime


class FinanceDashboard(models.TransientModel):
    _name = 'finance.dashboard'
    _description = 'Finance Dashboard'

    date_today = fields.Date(string='Today', default=lambda self: fields.Date.context_today(self))
    trend_range = fields.Selection([
        ('7', 'Last 7 Days'),
        ('30', 'Last 30 Days'),
    ], default='7', string='Range')
    sales_today = fields.Float(string='Today Sales', compute='_compute_metrics')
    vat_today = fields.Float(string='Today VAT', compute='_compute_metrics')
    orders_today = fields.Integer(string='Today Orders', compute='_compute_metrics')
    avg_basket_today = fields.Float(string='Avg Basket Today', compute='_compute_metrics')
    sales_week = fields.Float(string='This Week Sales', compute='_compute_metrics')
    vat_week = fields.Float(string='This Week VAT', compute='_compute_metrics')
    sales_month = fields.Float(string='This Month Sales', compute='_compute_metrics')
    vat_month = fields.Float(string='This Month VAT', compute='_compute_metrics')
    accounts_payable_total = fields.Float(string='Accounts Payable (Outstanding)', compute='_compute_metrics')
    accounts_payable_paid_month = fields.Float(string='Vendor Bills Paid (This Month)', compute='_compute_metrics')

    # HTML widgets
    sales_vat_last7_html = fields.Html(string='Sales & VAT (Last 7 Days)', compute='_compute_widgets')
    top_sellers_html = fields.Html(string='Top Sellers (Qty)', compute='_compute_widgets')
    fast_movers_html = fields.Html(string='Fast Movers', compute='_compute_widgets')
    ap_aging_html = fields.Html(string='AP Aging', compute='_compute_widgets')
    payments_badge_html = fields.Html(string='Payments Split (Badges)', compute='_compute_widgets')

    def _get_ranges(self):
        today = fields.Date.context_today(self)
        # week starts Monday
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        # month end not required for domain upper bound with <= today
        return today, week_start, week_end, month_start

    @api.depends('date_today')
    def _compute_metrics(self):
        for dash in self:
            today, week_start, week_end, month_start = dash._get_ranges()
            Tx = dash.env['finance.transaction']

            def _sum_tx(domain):
                data = Tx.read_group(domain, ['amount:sum', 'vat_amount:sum'], [])
                if data:
                    return data[0].get('amount_sum', 0.0), data[0].get('vat_amount_sum', 0.0)
                return 0.0, 0.0

            dash.sales_today, dash.vat_today = _sum_tx([
                ('transaction_type', '=', 'income'),
                ('date', '=', today),
            ])
            # Orders + avg basket today (final POS orders)
            ord_data = dash.env['pos.order'].read_group([
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('date_order', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
                ('date_order', '<=', fields.Datetime.to_string(datetime.combine(today, datetime.max.time()))),
            ], ['amount_total:sum', 'id:count'], [])
            if ord_data:
                dash.orders_today = int(ord_data[0].get('id_count', 0) or 0)
                total = ord_data[0].get('amount_total_sum', 0.0) or 0.0
                dash.avg_basket_today = (total / dash.orders_today) if dash.orders_today else 0.0
            else:
                dash.orders_today = 0
                dash.avg_basket_today = 0.0
            dash.sales_week, dash.vat_week = _sum_tx([
                ('transaction_type', '=', 'income'),
                ('date', '>=', week_start), ('date', '<=', week_end),
            ])
            dash.sales_month, dash.vat_month = _sum_tx([
                ('transaction_type', '=', 'income'),
                ('date', '>=', month_start), ('date', '<=', today),
            ])

            # Accounts payable total: sum residual on posted, unpaid vendor bills
            ap = dash.env['account.move'].read_group([
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'),
            ], ['amount_residual:sum'], [])
            dash.accounts_payable_total = (ap[0].get('amount_residual_sum') or ap[0].get('amount_residual', 0.0)) if ap else 0.0

            ap_paid = dash.env['account.move'].read_group([
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '=', 'paid'),
                ('invoice_date', '>=', month_start), ('invoice_date', '<=', today),
            ], ['amount_total:sum'], [])
            dash.accounts_payable_paid_month = (ap_paid[0].get('amount_total_sum') or ap_paid[0].get('amount_total', 0.0)) if ap_paid else 0.0

    # Action helpers to open filtered transactions
    def _open_tx_domain(self, domain, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'finance.transaction',
            'view_mode': 'list,form',
            'domain': domain,
        }

    def _open_sales_summary(self, start_dt, end_dt, title):
        # Open Sales Summary transient with date range context
        action = self.env.ref('finance_core.action_finance_sales_summary').read()[0]
        action['name'] = title
        action['context'] = {
            'default_date_from': fields.Date.to_date(start_dt),
            'default_date_to': fields.Date.to_date(end_dt),
        }
        return action

    def action_open_today_sales(self):
        self.ensure_one()
        tz_now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        start = tz_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = tz_now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return self._open_sales_summary(start, end, 'Today Sales')

    def action_open_week_sales(self):
        self.ensure_one()
        tz_now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        week_start = tz_now - timedelta(days=tz_now.weekday())
        start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = tz_now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return self._open_sales_summary(start, end, 'This Week Sales')

    def action_open_month_sales(self):
        self.ensure_one()
        tz_now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        start = tz_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = tz_now.replace(hour=23, minute=59, second=59, microsecond=999999)
        return self._open_sales_summary(start, end, 'This Month Sales')

    def action_open_ap_unpaid(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Accounts Payable (Unpaid)',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')],
        }

    def action_open_ap_paid_month(self):
        self.ensure_one()
        today, _, __, month_start = self._get_ranges()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Bills Paid (This Month)',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '=', 'paid'), ('invoice_date', '>=', month_start), ('invoice_date', '<=', today)],
        }

    def action_open_ap_overdue(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Accounts Payable (Overdue)',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid'), ('invoice_date_due', '<', today)],
        }

    def action_post_eod_today(self):
        self.ensure_one()
        self.env['finance.eod.service'].post_eod_for_date(fields.Date.context_today(self))
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    @api.depends('date_today', 'trend_range')
    def _compute_widgets(self):
        for dash in self:
            company_currency = dash.env.company.currency_id
            symbol = company_currency and company_currency.symbol or '$'
            today = fields.Date.context_today(dash)
            last_n = int(dash.trend_range or '7')
            startN = today - timedelta(days=last_n - 1)

            # Last 7 days Sales & VAT using finance.transaction (income)
            rg = dash.env['finance.transaction'].read_group(
                [('transaction_type', '=', 'income'), ('date', '>=', startN), ('date', '<=', today)],
                ['amount:sum', 'vat_amount:sum'], ['date:day']
            )
            rows = []
            by_date = {}
            for r in rg:
                key = r.get('date:day') or r.get('date')
                if isinstance(key, str):
                    try:
                        key = fields.Date.to_date(key)
                    except Exception:
                        # leave as-is if conversion fails
                        pass
                by_date[key] = (r.get('amount_sum', 0.0), r.get('vat_amount_sum', 0.0))
            for i in range(last_n):
                d = startN + timedelta(days=i)
                amt, vat = by_date.get(d, (0.0, 0.0))
                rows.append(f"<tr><td>{d}</td><td style='text-align:right'>{symbol}{amt:,.2f}</td><td style='text-align:right'>{symbol}{vat:,.2f}</td></tr>")
            dash.sales_vat_last7_html = (
                f"<div><h4>Sales &amp; VAT (Last {last_n} Days)</h4>"
                "<table class='o_list_view fd-table fd-table--blue'>"
                "<thead><tr>"
                "<th>Date</th>"
                "<th style='text-align:right'>Sales</th>"
                "<th style='text-align:right'>VAT</th>"
                "</tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table></div>"
            )

            # Top sellers by qty in last 7 days (POS lines)
            start_dt = datetime.combine(startN, datetime.min.time())
            end_dt = datetime.combine(today, datetime.max.time())
            rg_prod = dash.env['pos.order.line'].read_group(
                [('order_id.date_order', '>=', fields.Datetime.to_string(start_dt)),
                 ('order_id.date_order', '<=', fields.Datetime.to_string(end_dt)),
                 ('order_id.state', 'in', ['paid', 'done', 'invoiced'])],
                ['qty:sum', 'product_id'], ['product_id'], limit=5, orderby='qty desc'
            )
            total_qty = sum(r.get('qty', 0.0) for r in rg_prod) or 1.0
            li = []
            for r in rg_prod:
                name = r['product_id'][1]
                qty = r.get('qty', 0.0)
                pct = (qty / total_qty) * 100.0
                li.append(f"<li>{name} — {qty:,.0f} ({pct:.1f}%)</li>")
            dash.top_sellers_html = "<div><h4>Top Sellers (Qty)</h4><ul>" + ''.join(li) + "</ul></div>"
            # Override with table styling for better alignment and readability
            rows_top = []
            for r in rg_prod:
                prod_name = r['product_id'][1]
                qty = r.get('qty', 0.0)
                pct = (qty / total_qty) * 100.0
                rows_top.append(
                    f"<tr><td>{prod_name}</td><td style='text-align:right'>{qty:,.0f}</td><td style='text-align:right'>{pct:.1f}%</td></tr>"
                )
            dash.top_sellers_html = (
                "<div><h4>Top Sellers (Qty)</h4>"
                "<table class='o_list_view fd-table fd-table--green'>"
                "<thead><tr><th>Product</th><th style='text-align:right'>Qty</th><th style='text-align:right'>Share</th></tr></thead>"
                f"<tbody>{''.join(rows_top)}</tbody></table></div>"
            )

            # Fast movers: compare last 7 days vs previous 7 days
            prev_start = startN - timedelta(days=last_n)
            prev_end = startN - timedelta(days=1)
            prev_rg = dash.env['pos.order.line'].read_group(
                [('order_id.date_order', '>=', fields.Datetime.to_string(datetime.combine(prev_start, datetime.min.time()))),
                 ('order_id.date_order', '<=', fields.Datetime.to_string(datetime.combine(prev_end, datetime.max.time()))),
                 ('order_id.state', 'in', ['paid', 'done', 'invoiced'])],
                ['qty:sum', 'product_id'], ['product_id']
            )
            prev_map = {r['product_id'][0]: r.get('qty', 0.0) for r in prev_rg}
            movers = []
            for r in rg_prod:
                pid = r['product_id'][0]
                q_now = r.get('qty', 0.0)
                q_prev = prev_map.get(pid, 0.0)
                change = ((q_now - q_prev) / q_prev * 100.0) if q_prev else (100.0 if q_now else 0.0)
                movers.append((r['product_id'][1], change))
            movers.sort(key=lambda x: x[1], reverse=True)
            li2 = [f"<li>{n} — {c:+.1f}%</li>" for n, c in movers[:5]]
            dash.fast_movers_html = "<div><h4>Fast Movers (vs prev 7 days)</h4><ul>" + ''.join(li2) + "</ul></div>"
            # Override with table styling and color-coded change
            rows_mv = []
            for n, c in movers[:5]:
                cls = 'fd-change-pos' if c >= 0 else 'fd-change-neg'
                rows_mv.append(f"<tr><td>{n}</td><td style='text-align:right' class='{cls}'>{c:+.1f}%</td></tr>")
            dash.fast_movers_html = (
                "<div><h4>Fast Movers (vs prev 7 days)</h4>"
                "<table class='o_list_view fd-table fd-table--indigo'>"
                "<thead><tr><th>Product</th><th style='text-align:right'>Change</th></tr></thead>"
                f"<tbody>{''.join(rows_mv)}</tbody></table></div>"
            )

            # AP aging buckets
            today_dt = datetime.combine(today, datetime.max.time())
            def _sum(domain):
                res = dash.env['account.move'].read_group(domain, ['amount_residual:sum'], [])
                if res:
                    return res[0].get('amount_residual_sum') or res[0].get('amount_residual', 0.0)
                return 0.0
            dom_base = [('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')]
            current = _sum(dom_base + [('invoice_date_due', '>=', today)])
            b1 = _sum(dom_base + [('invoice_date_due', '<', today), ('invoice_date_due', '>=', today - timedelta(days=30))])
            b2 = _sum(dom_base + [('invoice_date_due', '<', today - timedelta(days=30)), ('invoice_date_due', '>=', today - timedelta(days=60))])
            b3 = _sum(dom_base + [('invoice_date_due', '<', today - timedelta(days=60)), ('invoice_date_due', '>=', today - timedelta(days=90))])
            b4 = _sum(dom_base + [('invoice_date_due', '<', today - timedelta(days=90))])
            dash.ap_aging_html = (
                "<div><h4>AP Aging</h4><table class='o_list_view fd-table fd-table--amber'>"
                "<thead><tr><th>Bucket</th><th style='text-align:right'>Amount</th></tr></thead><tbody>"
                f"<tr><td>Current</td><td style='text-align:right'>{symbol}{current:,.2f}</td></tr>"
                f"<tr><td>1-30</td><td style='text-align:right'>{symbol}{b1:,.2f}</td></tr>"
                f"<tr><td>31-60</td><td style='text-align:right'>{symbol}{b2:,.2f}</td></tr>"
                f"<tr><td>61-90</td><td style='text-align:right'>{symbol}{b3:,.2f}</td></tr>"
                f"<tr><td>&gt; 90</td><td style='text-align:right'>{symbol}{b4:,.2f}</td></tr>"
                "</tbody></table></div>"
            )

            # Payments badges (Today)
            pay_today = dash.env['pos.payment'].read_group([
                ('pos_order_id.state', 'in', ['paid', 'done', 'invoiced']),
                ('pos_order_id.date_order', '>=', fields.Datetime.to_string(datetime.combine(today, datetime.min.time()))),
                ('pos_order_id.date_order', '<=', fields.Datetime.to_string(datetime.combine(today, datetime.max.time()))),
            ], ['amount:sum', 'payment_method_id'], ['payment_method_id'])
            badges = []
            colors = ['#0ea5e9', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']
            for idx, r in enumerate(pay_today):
                name = r['payment_method_id'][1]
                amt = r.get('amount', 0.0)
                color = colors[idx % len(colors)]
                badges.append(f"<span class='badge' style='background:{color}1a;color:{color}'>{name}: {symbol}{amt:,.2f}</span>")
            dash.payments_badge_html = "<div class='fd-badges'>" + ''.join(badges) + "</div>"
