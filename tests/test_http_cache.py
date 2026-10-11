"""
Offline checks of the download cache: when a source cannot be reached, the next
files from that host are not retried (one connection timeout per outage, not one
per file), while an HTTP error such as a 403 does not mark the host as down.
Run:  python -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import http_cache  # noqa: E402

URL = "https://orbitguard-test.invalid/data.csv"


class TestUnreachableHost(unittest.TestCase):
    def setUp(self):
        http_cache._unreachable_until.clear()

    def tearDown(self):
        http_cache._unreachable_until.clear()

    def test_connection_failure_is_not_retried(self):
        with mock.patch.object(http_cache.requests, "get", side_effect=requests.ConnectionError("down")) as get:
            self.assertIsNone(http_cache.cached_text(URL, "orbitguard_test_missing_1.csv", 60))
            self.assertIsNone(http_cache.cached_text(URL + "?next", "orbitguard_test_missing_2.csv", 60))
        self.assertEqual(get.call_count, 1, "the second file must not wait out another timeout")
        self.assertTrue(http_cache.host_unreachable(URL))

    def test_http_error_does_not_mark_host_down(self):
        resp = mock.Mock()
        resp.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        with mock.patch.object(http_cache.requests, "get", return_value=resp):
            self.assertIsNone(http_cache.cached_text(URL, "orbitguard_test_missing_3.csv", 60))
        self.assertFalse(http_cache.host_unreachable(URL))


if __name__ == "__main__":
    unittest.main()
