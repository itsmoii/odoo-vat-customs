from odoo import api, fields, models
from socket import create_connection

def escpos_send(ip: str, data: bytes, port: int = 9100, timeout: float = 3.0):
    with create_connection((ip, port), timeout=timeout) as s:
        s.sendall(data)

def escpos_text(lines, codepage: int = 0):
    ESC, GS = b'\x1b', b'\x1d'
    buf = bytearray()
    buf += ESC + b'@' # init
    buf += ESC + b't' + bytes([codepage]) # codepage 0 (CP437) by default
    for line in lines:
        buf += (line or '').encode('cp437', errors='replace') + b'\n'
        buf += b'\n\n'
        buf += GS + b'V' + b'\x41' + b'\x03' # full cut
        return bytes(buf)

class PosPrintJob(models.Model):
    _name = 'pos.print.job'
    _description = 'POS Print Job'


    order_id = fields.Many2one('pos.order', required=True, ondelete='cascade', index=True)
    payload = fields.Text(required=True)           
    printer_ip = fields.Char(required=True)
    status = fields.Selection(
        [('pending', 'Pending'), ('done', 'Done'), ('error', 'Error')],
        default='pending', index=True
    )
    attempts = fields.Integer(default=0)
    error = fields.Text()

    @api.model
    def cron_process_jobs(self, batch=10, codepage=0):
        jobs = self.search([('status', '=', 'pending')], limit=batch, order='id asc')
        for job in jobs:
            try:
                data = escpos_text((job.payload or '').splitlines(), codepage=codepage)
                escpos_send(job.printer_ip, data)
                job.write({'status': 'done'})
            except Exception as e:
                job.write({
                    'status': 'error',
                    'attempts': job.attempts + 1,
                    'error': str(e),
                })

