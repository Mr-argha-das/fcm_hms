import os
from datetime import datetime

from core.paths import BASE_DIR
from models import SiteSettings


def get_site_settings() -> SiteSettings:
    settings = SiteSettings.objects.first()
    if settings:
        return settings

    settings = SiteSettings()
    settings.updated_at = datetime.utcnow()
    settings.save()
    return settings


def media_file_path(public_path: str | None) -> str | None:
    if not public_path:
        return None
    if public_path.startswith("/media/"):
        return os.path.join(BASE_DIR, public_path.lstrip("/"))
    if public_path.startswith("/uploads/"):
        return os.path.join(BASE_DIR, public_path.lstrip("/"))
    return public_path if os.path.isabs(public_path) else None
