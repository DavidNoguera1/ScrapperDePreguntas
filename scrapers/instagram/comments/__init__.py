"""Funcionalidad de scrapping de comentarios (y su filtrado de preguntas).

Todo lo especifico de extraer comentarios y clasificarlos como
preguntas/interes vive aqui, aislado del resto del proyecto. Las nuevas
funciones de scrapping (metricas, seguidores, etc.) deben ir en modulos
hermanos dentro de scrapers/instagram/ sin tocar este paquete.
"""

from scrapers.instagram.comments.scraper import CommentScraper

__all__ = ["CommentScraper"]
