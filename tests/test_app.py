import io
from unittest.mock import MagicMock, patch

import pytest

from app import build_link_table, extract_exif, extract_image_urls_from_dorks, fetch_image, gps_to_decimal


class TestBuildLinkTable:
    def test_empty_dorks(self):
        df = build_link_table({})
        assert df.empty

    def test_single_dork_with_urls(self):
        data = {
            "dorks": [
                {"type": "Credenciais", "urls": ["https://a.com", "https://b.com"]}
            ]
        }
        df = build_link_table(data)
        assert len(df) == 2
        assert list(df.columns) == ["Tipo da Dork", "URL Encontrada", "Ação"]
        assert df.iloc[0]["Tipo da Dork"] == "Credenciais"

    def test_multiple_dork_types(self):
        data = {
            "dorks": [
                {"type": "A", "urls": ["https://a.com"]},
                {"type": "B", "urls": ["https://b.com", "https://c.com"]},
            ]
        }
        df = build_link_table(data)
        assert len(df) == 3


class TestFetchImage:
    @patch("app.requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"\x89PNG"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        data, status = fetch_image("https://img.com/a.png", {})
        assert status == "ok"
        assert data == b"\x89PNG"

    @patch("app.requests.get")
    def test_forbidden(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_get.return_value = mock_resp

        data, status = fetch_image("https://img.com/a.png", {})
        assert status == "forbidden"
        assert data == b""

    @patch("app.requests.get", side_effect=Exception("timeout"))
    def test_error(self, mock_get):
        data, status = fetch_image("https://img.com/a.png", {})
        assert status == "error"
        assert data == b""


class TestExtractExif:
    def test_empty_bytes(self):
        assert extract_exif(b"") == {}

    def test_image_without_exif(self):
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buf, format="PNG")
        result = extract_exif(buf.getvalue())
        assert result == {}


class TestGpsToDecimal:
    def test_north_east(self):
        gps_info = {
            "GPSLatitude": ((40, 1), (26, 1), (46, 1)),
            "GPSLatitudeRef": "N",
            "GPSLongitude": ((79, 1), (58, 1), (56, 1)),
            "GPSLongitudeRef": "W",
        }
        lat, lon = gps_to_decimal(gps_info)
        assert abs(lat - 40.446111) < 0.01
        assert lon < 0  # West is negative


class TestExtractImageUrlsFromDorks:
    def test_empty_dorks(self):
        assert extract_image_urls_from_dorks({}) == []

    def test_extracts_images_from_fotos_e_imagens(self):
        data = {
            "dorks": [
                {
                    "type": "Fotos e Imagens",
                    "urls": [
                        "https://site.com/photo.jpg",
                        "https://site.com/doc.pdf",
                        "https://site.com/img.png",
                    ],
                }
            ]
        }
        result = extract_image_urls_from_dorks(data)
        assert result == ["https://site.com/photo.jpg", "https://site.com/img.png"]

    def test_extracts_images_from_fotos_em_redes_sociais(self):
        data = {
            "dorks": [
                {
                    "type": "Fotos em Redes Sociais",
                    "urls": ["https://site.com/pic.jpeg"],
                }
            ]
        }
        result = extract_image_urls_from_dorks(data)
        assert result == ["https://site.com/pic.jpeg"]

    def test_ignores_non_image_dork_types(self):
        data = {
            "dorks": [
                {
                    "type": "Perfis em Redes Sociais",
                    "urls": ["https://site.com/photo.jpg"],
                },
                {
                    "type": "Mencoes Publicas",
                    "urls": ["https://site.com/img.png"],
                },
            ]
        }
        result = extract_image_urls_from_dorks(data)
        assert result == []

    def test_mixed_dork_types(self):
        data = {
            "dorks": [
                {
                    "type": "Fotos e Imagens",
                    "urls": ["https://a.com/x.jpg"],
                },
                {
                    "type": "Perfis em Redes Sociais",
                    "urls": ["https://b.com/y.jpg"],
                },
                {
                    "type": "Fotos em Redes Sociais",
                    "urls": ["https://c.com/z.png"],
                },
            ]
        }
        result = extract_image_urls_from_dorks(data)
        assert result == ["https://a.com/x.jpg", "https://c.com/z.png"]
