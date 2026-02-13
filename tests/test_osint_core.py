import io
import json
from unittest.mock import MagicMock, patch

import instaloader
import pytest

from osint_core import OSINTCore


class TestOSINTCoreInit:
    def test_default_init(self):
        core = OSINTCore()
        assert core.delay_range == (3, 7)
        assert core.request_timeout == 15
        assert len(core.user_agents) == 4

    def test_custom_init(self):
        core = OSINTCore(delay_range=(1, 2), request_timeout=5, user_agents=["UA1"])
        assert core.delay_range == (1, 2)
        assert core.request_timeout == 5
        assert core.user_agents == ["UA1"]


class TestHelpers:
    def test_get_headers_returns_valid_ua(self):
        core = OSINTCore(user_agents=["TestAgent/1.0"])
        headers = core._get_headers()
        assert headers["User-Agent"] == "TestAgent/1.0"
        assert "Accept" in headers
        assert "Accept-Language" in headers

    def test_extract_ddg_url_direct(self):
        core = OSINTCore()
        assert core._extract_ddg_url("https://example.com") == "https://example.com"

    def test_extract_ddg_url_redirect(self):
        core = OSINTCore()
        url = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage"
        assert core._extract_ddg_url(url) == "https://example.com/page"

    def test_extract_ddg_url_no_uddg(self):
        core = OSINTCore()
        url = "https://duckduckgo.com/l/?other=val"
        assert core._extract_ddg_url(url) == url

    @patch("osint_core.time.sleep")
    def test_sleep_random(self, mock_sleep):
        core = OSINTCore(delay_range=(1, 1))
        core._sleep_random()
        mock_sleep.assert_called_once()
        delay = mock_sleep.call_args[0][0]
        assert 1.0 <= delay <= 1.0


class TestSearchWeb:
    @patch("osint_core.time.sleep")
    @patch("osint_core.requests.get")
    def test_search_web_parses_results(self, mock_get, _mock_sleep):
        html = """
        <html><body>
        <a class="result__a" href="https://example.com/1">Link 1</a>
        <a class="result__a" href="https://example.com/2">Link 2</a>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        core = OSINTCore()
        results = core.search_web("test query", max_results=10)
        assert results == ["https://example.com/1", "https://example.com/2"]

    @patch("osint_core.time.sleep")
    @patch("osint_core.requests.get")
    def test_search_web_respects_max_results(self, mock_get, _mock_sleep):
        html = """
        <html><body>
        <a class="result__a" href="https://a.com">A</a>
        <a class="result__a" href="https://b.com">B</a>
        <a class="result__a" href="https://c.com">C</a>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.text = html
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        core = OSINTCore()
        results = core.search_web("test", max_results=2)
        assert len(results) == 2


class TestAdvancedGoogleHacking:
    @patch.object(OSINTCore, "search_web", return_value=["https://r.com/1"])
    def test_runs_all_dorks(self, mock_search):
        core = OSINTCore()
        result = core.advanced_google_hacking("johndoe")
        assert result["target"] == "johndoe"
        assert len(result["dorks"]) == 4
        assert mock_search.call_count == 4

    @patch.object(OSINTCore, "search_web", return_value=["https://r.com/1"])
    def test_runs_selected_dorks(self, mock_search):
        core = OSINTCore()
        result = core.advanced_google_hacking(
            "johndoe", dork_types=["Mencoes Publicas"]
        )
        assert len(result["dorks"]) == 1
        assert result["dorks"][0]["type"] == "Mencoes Publicas"

    @patch.object(OSINTCore, "search_web", return_value=[])
    def test_dork_query_contains_target(self, mock_search):
        core = OSINTCore()
        core.advanced_google_hacking("johndoe")
        for call_args in mock_search.call_args_list:
            query = call_args[0][0]
            assert "johndoe" in query

    @patch.object(OSINTCore, "search_web", return_value=[])
    def test_unknown_dork_type_skipped(self, mock_search):
        core = OSINTCore()
        result = core.advanced_google_hacking("johndoe", dork_types=["NonExistent"])
        assert result["dorks"] == []
        mock_search.assert_not_called()


class TestImageDork:
    @patch.object(
        OSINTCore,
        "search_web",
        return_value=[
            "https://site.com/photo.jpg",
            "https://site.com/doc.pdf",
            "https://site.com/img.png",
        ],
    )
    def test_filters_image_extensions(self, mock_search):
        core = OSINTCore()
        result = core.image_dork("johndoe")
        assert "johndoe" in result["query"]
        assert len(result["urls"]) == 2
        assert "https://site.com/doc.pdf" not in result["urls"]


class TestInstagram:
    @patch("osint_core.instaloader.Profile.from_username")
    @patch("osint_core.instaloader.Instaloader")
    def test_get_profile_metadata(self, mock_loader_cls, mock_from_user):
        mock_profile = MagicMock()
        mock_profile.username = "testuser"
        mock_profile.biography = "hello"
        mock_profile.followers = 100
        mock_profile.followees = 50
        mock_profile.userid = 12345
        mock_profile.profile_pic_url = "https://pic.url"
        mock_profile.is_private = False
        mock_from_user.return_value = mock_profile

        core = OSINTCore()
        result = core.get_profile_metadata("testuser")
        assert result["username"] == "testuser"
        assert result["followers"] == 100
        assert result["following"] == 50
        assert result["is_private"] is False

    @patch("osint_core.instaloader.Profile.from_username", side_effect=Exception("not found"))
    @patch("osint_core.instaloader.Instaloader")
    def test_get_profile_metadata_error(self, mock_loader_cls, mock_from_user):
        core = OSINTCore()
        result = core.get_profile_metadata("baduser")
        assert "error" in result
        assert result["username"] == "baduser"

    @patch(
        "osint_core.instaloader.Profile.from_username",
        side_effect=instaloader.TooManyRequestsException("429 Too Many Requests"),
    )
    @patch("osint_core.instaloader.Instaloader")
    def test_get_profile_metadata_rate_limited(self, mock_loader_cls, mock_from_user):
        core = OSINTCore()
        result = core.get_profile_metadata("ratelimited")
        assert result["username"] == "ratelimited"
        assert "error" in result
        assert "429" in result["error"]


class TestPrivateSniffer:
    @patch.object(OSINTCore, "search_web", return_value=["https://ig.com/p/abc"])
    def test_returns_query_and_urls(self, mock_search):
        core = OSINTCore()
        result = core.private_sniffer("someuser")
        assert result["username"] == "someuser"
        assert "collab" in result["query"]
        assert "tagged" in result["query"]
        assert len(result["urls"]) == 1


class TestMonitorFollowers:
    @patch.object(
        OSINTCore,
        "get_profile_metadata",
        return_value={"username": "u", "followers": 150},
    )
    def test_computes_delta(self, mock_meta):
        core = OSINTCore()
        result = core.monitor_followers("u", 100)
        assert result["current_followers"] == 150
        assert result["delta"] == 50
        assert result["status"] == "ok"

    @patch.object(
        OSINTCore,
        "get_profile_metadata",
        return_value={"username": "u", "error": "fail"},
    )
    def test_handles_error(self, mock_meta):
        core = OSINTCore()
        result = core.monitor_followers("u", 100)
        assert result["status"] == "error"


class TestToJson:
    def test_to_json(self):
        data = {"key": "value", "num": 42}
        result = OSINTCore.to_json(data)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["num"] == 42
