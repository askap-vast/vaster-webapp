"""
Test settings — extends the main settings file with overrides that remove
Docker-specific paths so the test suite can run on a developer machine or in
CI without needing the container's filesystem layout.

Usage:
    pytest  (from repo root — configured via pytest.ini)

The os.environ.setdefault() calls below must happen *before* the wildcard
import, because settings.py reads several env vars at module-import time.
setdefault() does not override values already present in the environment,
so CI can still inject its own credentials.
"""

import os
import tempfile

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DB_NAME", "ywangvaster")
os.environ.setdefault("DB_USERNAME", "ywangvaster")
os.environ.setdefault("DB_PASSWORD", "vast1234star")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DEBUG", "1")
os.environ.setdefault("DJANGO_LOG_LEVEL", "WARNING")

from ywangvaster_webapp.settings import *  # noqa: F401, F403, E402

# Replace the file handler (which writes to /home/app/logs/webapp.log) with a
# null handler so tests don't require the Docker container's filesystem.
LOGGING["handlers"]["file"] = {  # noqa: F405
    "class": "logging.NullHandler",
}

# Use a temporary directory for media uploads during tests so file-upload
# tests don't write to /ywangvaster_media (which doesn't exist outside Docker).
MEDIA_ROOT = tempfile.mkdtemp(prefix="vaster_test_media_")
