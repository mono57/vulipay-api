import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from storages.backends.s3boto3 import S3Boto3Storage


class ProfilePictureStorage(S3Boto3Storage):
    """
    Custom storage for profile pictures using S3.

    Generates UUID-based filenames in uppercase with no hyphens.
    If USE_S3_STORAGE is False, falls back to default storage.
    """

    def __init__(self, *args, **kwargs):
        if not getattr(settings, "USE_S3_STORAGE", False):
            self.use_default_storage = True
            return

        self.use_default_storage = False
        kwargs.setdefault("bucket_name", settings.AWS_STORAGE_BUCKET_NAME)
        kwargs.setdefault("location", settings.AWS_LOCATION)
        kwargs.setdefault(
            "default_acl", getattr(settings, "AWS_DEFAULT_ACL", "public-read")
        )

        super().__init__(*args, **kwargs)

    def _save(self, name, content):
        if getattr(self, "use_default_storage", False):
            return default_storage._save(name, content)
        return super()._save(name, content)

    def get_available_name(self, name, max_length=None):
        """
        Returns a filename based on the original filename but with a UUID prefix
        and no path information.
        """
        # Extract the file extension
        ext = name.split(".")[-1] if "." in name else ""

        # Generate UUID in uppercase with no hyphens
        uuid_name = str(uuid.uuid4()).replace("-", "").upper()

        # Build new filename with the same extension
        if ext:
            uuid_name = f"{uuid_name}.{ext}"

        # The file will be stored in the profile_pictures/ directory on S3
        return f"profile_pictures/{uuid_name}"

    def url(self, name):
        if getattr(self, "use_default_storage", False):
            return default_storage.url(name)
        return super().url(name)

    def path(self, name):
        """
        Return a local filesystem path where the file can be retrieved.
        For S3, this is not available, so we'll return None if using S3.
        """
        if getattr(self, "use_default_storage", False):
            return default_storage.path(name)
        # S3 doesn't support path, but we'll handle this gracefully for testing
        raise NotImplementedError("S3 storage doesn't support absolute paths.")
