from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from app.accounts.cache import (
    COUNTRY_IDS_CACHE_KEY,
    get_cache_stats,
    get_valid_country_ids,
    is_valid_country_id,
    refresh_country_ids_cache,
)
from app.accounts.models import AvailableCountry


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
            "KEY_PREFIX": "vulipay",
        }
    }
)
class CountryCacheTestCase(TestCase):
    def setUp(self):
        # Clear cache before each test
        cache.clear()

        # Create test countries
        self.country1 = AvailableCountry.objects.create(
            name="Test Country 1",
            dial_code="123",
            iso_code="TC1",
            phone_number_regex="",
        )
        self.country2 = AvailableCountry.objects.create(
            name="Test Country 2",
            dial_code="456",
            iso_code="TC2",
            phone_number_regex="",
        )

    def test_get_valid_country_ids(self):
        cache.delete(COUNTRY_IDS_CACHE_KEY)

        with patch("app.accounts.cache.logger") as mock_logger:
            country_ids = get_valid_country_ids()
            mock_logger.info.assert_called_with("Country IDs cache refreshed")

        self.assertIn(self.country1.id, country_ids)
        self.assertIn(self.country2.id, country_ids)

        with patch("app.accounts.cache.logger") as mock_logger:
            country_ids_again = get_valid_country_ids()
            mock_logger.info.assert_not_called()

        self.assertEqual(country_ids, country_ids_again)

    def test_refresh_country_ids_cache(self):
        # Set a fake value in the cache
        fake_ids = {9999}
        cache.set(COUNTRY_IDS_CACHE_KEY, fake_ids)

        # Verify we get the fake value
        self.assertEqual(get_valid_country_ids(), fake_ids)

        # Refresh should update the cache
        refreshed_ids = refresh_country_ids_cache()

        # Now should contain real country IDs
        self.assertIn(self.country1.id, refreshed_ids)
        self.assertIn(self.country2.id, refreshed_ids)

        # Verify get_valid_country_ids returns the refreshed data
        self.assertEqual(get_valid_country_ids(), refreshed_ids)

    def test_is_valid_country_id(self):
        # Valid country ID should return True
        self.assertTrue(is_valid_country_id(self.country1.id))

        # Invalid country ID should return False
        self.assertFalse(is_valid_country_id(9999))

        # None should return False
        self.assertFalse(is_valid_country_id(None))

    def test_cache_updates_on_model_changes(self):
        # Ensure cache is populated before testing
        refresh_country_ids_cache()

        # Get initial ids
        initial_ids = get_valid_country_ids()

        # Create a new country
        new_country = AvailableCountry.objects.create(
            name="New Country",
            dial_code="789",
            iso_code="NEW",
            phone_number_regex="",
        )

        # Cache should have been updated by the signal
        updated_ids = get_valid_country_ids()
        self.assertIn(new_country.id, updated_ids)

        # Delete a country
        new_country.delete()

        # Cache should have been updated again
        after_delete_ids = get_valid_country_ids()
        self.assertNotIn(new_country.id, after_delete_ids)

    @patch("app.accounts.cache.get_redis_connection")
    def test_get_cache_stats(self, mock_get_redis_connection):
        # Mock the Redis connection and info method
        mock_redis = Mock()
        mock_info = {
            "keyspace_hits": 100,
            "keyspace_misses": 10,
            "used_memory_human": "1MB",
            "connected_clients": 5,
            "uptime_in_seconds": 3600,
        }
        mock_redis.info.return_value = mock_info
        mock_redis.ttl.return_value = 86400  # 24 hours in seconds

        mock_get_redis_connection.return_value = mock_redis

        # Call the function
        stats = get_cache_stats()

        # Verify results
        self.assertEqual(stats["hits"], 100)
        self.assertEqual(stats["misses"], 10)
        self.assertEqual(stats["memory_used"], "1MB")
        self.assertEqual(stats["connected_clients"], 5)
        self.assertEqual(stats["uptime_in_seconds"], 3600)
        self.assertEqual(stats["country_ids_ttl_seconds"], 86400)

    @patch("app.accounts.cache.get_redis_connection")
    def test_get_cache_stats_error_handling(self, mock_get_redis_connection):
        # Mock the Redis connection to raise an exception
        mock_redis = Mock()
        mock_redis.info.side_effect = Exception("Connection error")
        mock_get_redis_connection.return_value = mock_redis

        # Call the function
        with patch("app.accounts.cache.logger") as mock_logger:
            stats = get_cache_stats()

        # Verify results
        self.assertIn("error", stats)
        self.assertEqual(stats["error"], "Connection error")
        mock_logger.error.assert_called_once()
        self.assertIn("Error getting Redis stats", mock_logger.error.call_args[0][0])

    @override_settings(DEBUG=True)
    def test_get_valid_country_ids_debug_mode(self):
        # Clear cache to ensure cache miss
        cache.delete(COUNTRY_IDS_CACHE_KEY)

        # In DEBUG mode, if cache is empty, it should return None
        with patch("app.accounts.cache.refresh_country_ids_cache") as mock_refresh:
            # Call the function
            result = get_valid_country_ids()

            # Verify the function returned None and didn't call refresh_country_ids_cache
            self.assertIsNone(result)
            mock_refresh.assert_not_called()
