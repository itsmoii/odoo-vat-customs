import logging
from . import models

_logger = logging.getLogger(__name__)

# Lazy import of real hooks file
try:
    from . import hooks as _hooks
except Exception as e:  # pragma: no cover
    _hooks = None
    _logger.warning(" Could not import hooks.py: %s", e)


def pre_init_cleanup(cr):
    if _hooks and hasattr(_hooks, 'pre_init_cleanup'):
        return _hooks.pre_init_cleanup(cr)
    _logger.info("ℹ pre_init_cleanup skipped (no hooks module loaded).")


def post_init_setup(cr, registry):
    if _hooks and hasattr(_hooks, 'post_init_setup'):
        return _hooks.post_init_setup(cr, registry)
    _logger.info("ℹ post_init_setup skipped (no hooks module loaded).")


def post_load_cleanup(cr, registry):
    if _hooks and hasattr(_hooks, 'post_load_cleanup'):
        return _hooks.post_load_cleanup(cr, registry)
    _logger.info("ℹ post_load_cleanup skipped (no hooks module loaded).")
