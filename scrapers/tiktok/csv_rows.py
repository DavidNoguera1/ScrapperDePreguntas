from datetime import datetime, timezone

from core.config import fmt_dia, fmt_mes


def build_profile_video_row(username, video):
    published_at = _published_at(video.get("create_time"))
    duration = video.get("duration")

    return {
        "Dia": fmt_dia(published_at) if published_at else "",
        "Cuenta": username,
        "Red Social": "TikTok",
        "Tipo de publicacion": "Carrusel" if duration == 0 else "Video",
        "Enlace": video.get("url", ""),
        "Comentario": video.get("title", ""),
        "Tema principal": "",
        "Mes": fmt_mes(published_at) if published_at else "",
        "duracion": "" if duration is None else duration,
        "Titulo": video.get("title", ""),
        "Likes": video.get("likes", 0),
        "Comentarios": video.get("comments", 0),
        "Guardados": video.get("saves", 0),
        "Compartidos": video.get("shares", 0),
        "Reproducciones": video.get("plays", 0),
        "Fecha publicacion": (
            published_at.strftime("%Y-%m-%d %H:%M:%S") if published_at else ""
        ),
    }


def _published_at(create_time):
    if not create_time:
        return None
    try:
        return datetime.fromtimestamp(int(create_time), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
