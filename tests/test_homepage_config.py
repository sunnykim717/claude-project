import json
import unittest
from pathlib import Path

from homepage_config.convert import ConfigError, convert, load_designs

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "homepage_config" / "template.json"


def _template():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def _luminance(hex_color):
    n = int(hex_color[1:], 16)
    channels = []
    for shift in (16, 8, 0):
        c = ((n >> shift) & 255) / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(a, b):
    hi, lo = sorted([_luminance(a), _luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class TemplateConversionTest(unittest.TestCase):
    def test_template_converts_without_errors(self):
        site, warnings = convert(_template())
        self.assertEqual(site["title"], "새로운 기관")
        self.assertEqual(site["theme"]["accent"], "#2563EB")
        self.assertEqual(site["cta"], {"label": "자세히 보기", "url": "#about"})
        self.assertEqual(site["sections"][0], "cta")
        self.assertTrue(any("logo" in w for w in warnings))

    def test_navigation_maps_to_page_sections(self):
        site, _ = convert(_template())
        hrefs = {entry["label"]: entry["href"] for entry in site["nav"]}
        self.assertEqual(hrefs["기관소개"], "#about")
        self.assertEqual(hrefs["문의"], "#contact")

    def test_unknown_navigation_path_is_skipped_with_warning(self):
        config = _template()
        config["navigation"].append({"label": "갤러리", "path": "/gallery"})
        site, warnings = convert(config)
        self.assertNotIn("갤러리", [e["label"] for e in site["nav"]])
        self.assertTrue(any("갤러리" in w for w in warnings))

    def test_unknown_design_name_is_an_error(self):
        config = _template()
        config["design"] = "없는-디자인"
        with self.assertRaises(ConfigError):
            convert(config)

    def test_explicit_theme_overrides_design_preset(self):
        config = _template()
        config["design"] = "warm-orange"
        config["theme"] = {"primaryColor": "#123456"}
        site, _ = convert(config)
        self.assertEqual(site["theme"]["accent"], "#123456")
        self.assertEqual(site["theme"]["radius"], 4)

    def test_bad_color_and_language_reported_together(self):
        config = _template()
        config["theme"]["primaryColor"] = "blue"
        config["site"]["language"] = "fr"
        with self.assertRaises(ConfigError) as ctx:
            convert(config)
        self.assertEqual(len(ctx.exception.errors), 2)

    def test_javascript_link_is_refused(self):
        config = _template()
        config["homepage"]["hero"]["buttonLink"] = "javascript:alert(1)"
        site, warnings = convert(config)
        self.assertNotIn("cta", site)
        self.assertTrue(any("버튼" in w for w in warnings))


class DesignPresetTest(unittest.TestCase):
    def test_every_preset_has_readable_text_and_button_contrast(self):
        for name, design in load_designs().items():
            with self.subTest(design=name):
                self.assertGreaterEqual(_contrast(design["textColor"], design["backgroundColor"]), 4.5)
                self.assertGreaterEqual(_contrast(design["backgroundColor"], design["primaryColor"]), 4.5)

    def test_every_preset_converts(self):
        for name in load_designs():
            with self.subTest(design=name):
                config = _template()
                config["design"] = name
                site, _ = convert(config)
                self.assertTrue(site["theme"]["accent"].startswith("#"))


if __name__ == "__main__":
    unittest.main()
