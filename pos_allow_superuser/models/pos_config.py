from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def open_ui(self):
        """Allow superuser to open POS UI by removing the hard block.

        This is the same as the core method but without the superuser check.
        """
        self.ensure_one()

        if not self.current_session_id:
            self._check_before_creating_new_session()
        self._validate_fields(self._fields)

        return self._action_to_open_ui()

