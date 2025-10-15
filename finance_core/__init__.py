from . import models
# Expose post-init hook
try:
    from .hooks import post_init_assign_taxes  # noqa: F401
except Exception:
    post_init_assign_taxes = None
