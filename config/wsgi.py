import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent

sys.path.append(str(ROOT_DIR / "app"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

application = get_wsgi_application()
