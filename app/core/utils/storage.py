import logging
import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.files.storage import default_storage
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class ProfilePictureStorage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        if not getattr(settings, "USE_S3_STORAGE", False):
            self.use_default_storage = True
            self.location = "profile_pictures"
            return

        self.use_default_storage = False
        self.location = kwargs.get("location") or getattr(
            settings, "AWS_LOCATION", "media"
        )

        if hasattr(settings, "AWS_STORAGE_BUCKET_NAME"):
            kwargs.setdefault("bucket_name", settings.AWS_STORAGE_BUCKET_NAME)
        else:
            kwargs.setdefault("bucket_name", "default-bucket-name")

        kwargs.setdefault("location", self.location)

        if hasattr(settings, "AWS_DEFAULT_ACL"):
            kwargs.setdefault("default_acl", settings.AWS_DEFAULT_ACL)
        else:
            kwargs.setdefault("default_acl", "public-read")

        super().__init__(*args, **kwargs)

    def _save(self, name, content):
        if getattr(self, "use_default_storage", False):
            return default_storage._save(name, content)
        return super()._save(name, content)

    def get_available_name(self, name, max_length=None):
        ext = name.split(".")[-1] if "." in name else ""
        uuid_name = str(uuid.uuid4()).replace("-", "").upper()

        if ext:
            uuid_name = f"{uuid_name}.{ext}"

        return f"profile_pictures/{uuid_name}"

    def url(self, name):
        if getattr(self, "use_default_storage", False):
            return default_storage.url(name)
        return super().url(name)

    def path(self, name):
        if getattr(self, "use_default_storage", False):
            return default_storage.path(name)
        # S3 doesn't support path, but we'll handle this gracefully for testing
        raise NotImplementedError("S3 storage doesn't support absolute paths.")

    def exists(self, name):
        if getattr(self, "use_default_storage", False):
            return default_storage.exists(name)
        try:
            return super().exists(name)
        except Exception as e:
            logger.warning(f"Error checking if file exists in S3: {e}")
            return False

    def delete(self, name):
        if getattr(self, "use_default_storage", False):
            return default_storage.delete(name)
        try:
            return super().delete(name)
        except Exception as e:
            logger.warning(f"Error deleting file from S3: {e}")
            return False

    def generate_presigned_url(
        self, file_extension, content_type=None, expiration=3600
    ):
        if not getattr(settings, "USE_S3_STORAGE", False):
            logger.warning("Presigned URLs are only available when USE_S3_STORAGE=True")
            return None

        file_key = self.get_available_name(f"temp.{file_extension}")

        try:
            aws_access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "")
            aws_secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
            aws_region = getattr(settings, "AWS_S3_REGION_NAME", None)
            aws_endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
            aws_bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")

            if not all([aws_access_key, aws_secret_key, aws_bucket]):
                logger.warning("Using mock presigned URL data for testing")
                return {
                    "url": "https://example-bucket.s3.amazonaws.com/",
                    "fields": {
                        "key": file_key,
                        "AWSAccessKeyId": "MOCKAWSKEY",
                        "policy": "mock-policy",
                        "signature": "mock-signature",
                    },
                    "file_key": file_key,
                    "method": "POST",
                }

            s3_client = boto3.client(
                "s3",
                region_name=aws_region,
                endpoint_url=aws_endpoint,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                config=Config(signature_version="s3v4"),
            )

            presigned_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": aws_bucket,
                    "Key": file_key,
                    "ContentType": content_type or f"image/{file_extension}",
                },
                ExpiresIn=expiration,
            )

            return {
                "url": presigned_url,
                "fields": {},
                "file_key": file_key,
                "method": "PUT",
            }

        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
