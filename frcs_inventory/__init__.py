
from . import controllers
from . import models

# Expose post_init_hook for the manifest
try:
    from .hooks import post_init_hook  # noqa: F401
except Exception:
    # Keep module import resilient even if hooks change
    post_init_hook = None
 
