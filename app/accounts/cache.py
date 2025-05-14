import logging
from functools import wraps

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_redis import get_redis_connection

from app.accounts.models import AvailableCountry

logger = logging.getLogger(__name__)

COUNTRY_IDS_CACHE_KEY = "available_country_ids"
CACHE_TIMEOUT = 60 * 60 * 24


def get_valid_country_ids():
    country_ids = cache.get(COUNTRY_IDS_CACHE_KEY)
    print(country_ids)
    if not country_ids:
        logger.info("Country IDs cache miss, fetching from database")
        country_ids = set(AvailableCountry.objects.values_list("id", flat=True))
        cache.set(COUNTRY_IDS_CACHE_KEY, country_ids, CACHE_TIMEOUT)

    return country_ids


def refresh_country_ids_cache():
    """Force refresh the country IDs cache."""
    country_ids = set(AvailableCountry.objects.values_list("id", flat=True))
    cache.set(COUNTRY_IDS_CACHE_KEY, country_ids, CACHE_TIMEOUT)
    logger.info("Country IDs cache refreshed")
    return country_ids


def is_valid_country_id(country_id):
    if country_id is None:
        return False

    country_ids = get_valid_country_ids()
    return country_id in country_ids


def get_cache_stats():
    try:
        conn = get_redis_connection("default")
        stats = {
            "hits": conn.info().get("keyspace_hits", 0),
            "misses": conn.info().get("keyspace_misses", 0),
            "memory_used": conn.info().get("used_memory_human", "N/A"),
            "connected_clients": conn.info().get("connected_clients", 0),
            "uptime_in_seconds": conn.info().get("uptime_in_seconds", 0),
        }

        ttl = conn.ttl(f"vulipay:{COUNTRY_IDS_CACHE_KEY}")
        if ttl > 0:
            stats["country_ids_ttl_seconds"] = ttl
        else:
            stats["country_ids_ttl_seconds"] = "Key not found or no expiry"

        return stats
    except Exception as e:
        logger.error(f"Error getting Redis stats: {str(e)}")
        return {"error": str(e)}


@receiver(post_save, sender=AvailableCountry)
def update_country_cache_on_save(sender, instance, **kwargs):
    refresh_country_ids_cache()


@receiver(post_delete, sender=AvailableCountry)
def update_country_cache_on_delete(sender, instance, **kwargs):
    refresh_country_ids_cache()
