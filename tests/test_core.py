import csv
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

import main
from instagram_scraper import (
    InstagramScraper,
    is_interesting_comment,
    is_user_comment,
)


class CsvTests(unittest.TestCase):
    def test_live_csv_round_trip_preserves_punctuation_and_newlines(self):
        previous_csv = main.CSV_FILE
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "roundtrip.csv"
                main.CSV_FILE = str(path)
                with path.open("w", encoding="utf-8-sig", newline="") as handle:
                    csv.DictWriter(
                        handle,
                        fieldnames=main.CSV_HEADERS,
                        delimiter=";",
                    ).writeheader()

                expected = {header: "" for header in main.CSV_HEADERS}
                expected.update({
                    "Dia": "08-jul",
                    "Cuenta": "prueba",
                    "Comentario": 'Hola, uso ; y "comillas"\ncon salto',
                })
                main.append_csv(expected)

                with path.open(encoding="utf-8-sig", newline="") as handle:
                    actual = next(csv.DictReader(handle, delimiter=";"))
                self.assertEqual(actual, expected)
        finally:
            main.CSV_FILE = previous_csv


class InstagramTests(unittest.TestCase):
    def test_short_questions_are_not_discarded(self):
        self.assertTrue(is_user_comment("¿NIE?"))
        self.assertFalse(is_user_comment("15h"))
        self.assertFalse(is_user_comment("2w"))
        self.assertFalse(is_user_comment("1d · Edited"))
        self.assertTrue(InstagramScraper._is_question("¿Qué tasa pago?"))
        self.assertFalse(
            InstagramScraper._is_question("Necesito ayuda con mi trámite")
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
                comments = InstagramScraper._extract_comments(page)
                post_date = InstagramScraper._extract_post_date(page)
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
                comments = InstagramScraper._extract_comments(page)
            finally:
                browser.close()

        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["text"], "¿Puedo renovar mi residencia?")


if __name__ == "__main__":
    unittest.main()
