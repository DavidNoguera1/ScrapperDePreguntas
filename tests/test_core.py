import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from core import csv_handler as ch
from core.config import CSV_HEADERS
from core.filters import is_interesting_comment, is_user_comment, is_question
from main import _parse_instagram_cli_date
from scrapers.instagram.scraper import InstagramScraper
from scrapers.instagram.extractors import extract_comments, extract_post_date
from scrapers.tiktok.csv_rows import build_profile_video_row
from scrapers.tiktok.extractors import filter_videos_by_date, parse_video_metrics


class CsvTests(unittest.TestCase):
    def test_live_csv_round_trip_preserves_punctuation_and_newlines(self):
        previous_csv = ch.CSV_FILE
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "roundtrip.csv"
                ch.CSV_FILE = str(path)
                with path.open("w", encoding="utf-8-sig", newline="") as handle:
                    csv.DictWriter(
                        handle,
                        fieldnames=CSV_HEADERS,
                        delimiter=";",
                    ).writeheader()

                expected = {header: "" for header in CSV_HEADERS}
                expected.update({
                    "Dia": "08-jul",
                    "Cuenta": "prueba",
                    "Comentario": 'Hola, uso ; y "comillas"\ncon salto',
                })
                ch.append_csv(expected)

                with path.open(encoding="utf-8-sig", newline="") as handle:
                    actual = next(csv.DictReader(handle, delimiter=";"))
                self.assertEqual(actual, expected)
        finally:
            ch.CSV_FILE = previous_csv


class InstagramTests(unittest.TestCase):
    def test_instagram_dates_use_dd_mm_yyyy_and_include_the_end_day(self):
        start = _parse_instagram_cli_date("01-06-2026")
        end = _parse_instagram_cli_date("30-06-2026").replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        self.assertEqual(start.date().isoformat(), "2026-06-01")
        self.assertTrue(
            InstagramScraper._is_post_in_range(
                datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
                start,
                end,
            )
        )
        self.assertFalse(
            InstagramScraper._is_post_in_range(
                datetime(2026, 7, 1, tzinfo=timezone.utc), start, end
            )
        )

    def test_short_questions_are_not_discarded(self):
        self.assertTrue(is_user_comment("¿NIE?"))
        self.assertFalse(is_user_comment("15h"))
        self.assertFalse(is_user_comment("2w"))
        self.assertFalse(is_user_comment("1d · Edited"))
        self.assertTrue(is_question("¿Qué tasa pago?"))
        self.assertFalse(
            is_question("Necesito ayuda con mi trámite")
        )

    def test_interest_filter_matches_reference_style(self):
        self.assertTrue(
            is_interesting_comment(
                "¿Puedo renovar mi NIE aunque el expediente siga en trámite?"
            )
        )
        self.assertTrue(
            is_interesting_comment(
                "Hay empresas que no aceptan ese permiso para trabajar."
            )
        )
        self.assertTrue(
            is_interesting_comment(
                "El enlace de la cita es https://example.com/appointment/10"
            )
        )
        self.assertFalse(is_interesting_comment("Excelente video ❤️❤️"))
        self.assertFalse(is_interesting_comment("15h"))

    def test_structured_comment_and_post_date_extraction(self):
        html = """
        <main>
          <time datetime="2026-06-01T10:00:00.000Z">June 1</time>
          <div class="comment">
            <div>
              <a href="/persona/">persona</a>
              <a href="/cuenta/p/ABC/c/123/">
                <time datetime="2026-06-02T11:00:00.000Z">1d</time>
              </a>
            </div>
            <span dir="auto">¿Qué tasa pago, la 790?</span>
          </div>
        </main>
        """
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_content(html)
                comments = extract_comments(page)
                post_date = extract_post_date(page)
            finally:
                browser.close()

        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["text"], "¿Qué tasa pago, la 790?")
        self.assertEqual(post_date.date().isoformat(), "2026-06-01")

    def test_timestamp_sibling_is_not_mistaken_for_comment(self):
        html = """
        <main>
          <time datetime="2026-06-01T10:00:00.000Z">June 1</time>
          <div class="comment">
            <div>
              <a href="/persona/">persona</a>
              <a href="/cuenta/p/ABC/c/456/">
                <time datetime="2026-06-02T11:00:00.000Z"></time>
              </a>
              <span dir="auto">15h</span>
            </div>
            <span dir="auto">¿Puedo renovar mi residencia?</span>
          </div>
        </main>
        """
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.set_content(html)
                comments = extract_comments(page)
            finally:
                browser.close()

        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["text"], "¿Puedo renovar mi residencia?")

class TikTokProfileMetricsTests(unittest.TestCase):
    def test_profile_row_uses_publication_day_and_duration(self):
        published = datetime(2026, 7, 23, 14, 24, 36, tzinfo=timezone.utc)
        metrics = parse_video_metrics({
            "id": "123",
            "desc": "Carrusel de prueba",
            "createTime": int(published.timestamp()),
            "author": {"uniqueId": "entretramites"},
            "video": {"duration": 0},
            "stats": {
                "diggCount": 13,
                "commentCount": 2,
                "collectCount": 5,
                "shareCount": 1,
                "playCount": 2145,
            },
        })

        row = build_profile_video_row("entretramites", metrics)

        self.assertEqual(row["Dia"], "23-jul")
        self.assertEqual(row["Mes"], "Julio")
        self.assertEqual(row["duracion"], 0)
        self.assertEqual(row["Tipo de publicacion"], "Carrusel")
        self.assertEqual(row["Fecha publicacion"], "2026-07-23 14:24:36")

    def test_end_date_at_midnight_includes_the_whole_day(self):
        videos = [
            {
                "id": "included",
                "create_time": int(
                    datetime(2026, 7, 27, 23, 59, 59, tzinfo=timezone.utc).timestamp()
                ),
            },
            {
                "id": "excluded",
                "create_time": int(
                    datetime(2026, 7, 28, 0, 0, 0, tzinfo=timezone.utc).timestamp()
                ),
            },
        ]

        filtered = filter_videos_by_date(
            videos,
            start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 7, 27, tzinfo=timezone.utc),
        )

        self.assertEqual([video["id"] for video in filtered], ["included"])


if __name__ == "__main__":
    unittest.main()
