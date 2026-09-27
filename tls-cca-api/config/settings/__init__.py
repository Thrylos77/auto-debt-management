"""TLS CCA Django settings package.

``config.settings`` remains the default DJANGO_SETTINGS_MODULE for compatibility.
Set ``DJANGO_ENV`` to ``development``, ``test`` or ``production`` to select the
corresponding overlay.
"""

import os

from .base import *  # noqa: F401,F403

_ENV = os.getenv("DJANGO_ENV", "base").strip().lower()
if _ENV == "development":
    from .development import *  # noqa: F401,F403
elif _ENV == "test":
    from .test import *  # noqa: F401,F403
elif _ENV == "production":
    from .production import *  # noqa: F401,F403
