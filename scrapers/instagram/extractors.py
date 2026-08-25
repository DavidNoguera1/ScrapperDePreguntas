"""Extractores DOM genericos de Instagram (independientes del tipo de dato).

Solo utilidades reutilizables por cualquier funcion de scrapping
(fechas de publicacion, etc.). La extraccion de comentarios vive en
scrapers/instagram/comments/extractors.py.
"""

from datetime import datetime


def extract_post_date(page):
    value = page.evaluate(
        """() => {
            const times = Array.from(document.querySelectorAll('time'));
            const postTime = times.find(time => {
                const link = time.closest('a');
                return !link || !String(link.getAttribute('href') || '').includes('/c/');
            });
            return postTime ? postTime.getAttribute('datetime') : null;
        }"""
    )
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
