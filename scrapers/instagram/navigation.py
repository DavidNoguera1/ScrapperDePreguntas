import re
import logging


LOGGER = logging.getLogger(__name__)


def route_lightweight(route):
    if route.request.resource_type in {"image", "media", "font"}:
        route.abort()
    else:
        route.continue_()


def is_authenticated(context, page):
    cookie_names = {cookie["name"] for cookie in context.cookies()}
    return (
        "sessionid" in cookie_names
        and "login" not in page.url.casefold()
        and "checkpoint" not in page.url.casefold()
    )


def discover_profile_links(page, username, max_posts=None):
    username_re = re.escape(username)
    own_resource = re.compile(
        rf"^https://www\.instagram\.com/{username_re}/(?:p|reel)/[^/?#]+/?$",
        re.IGNORECASE,
    )
    ordered_links = {}
    stable_rounds = 0

    for _ in range(30):
        raw_links = page.locator("main a[href]").evaluate_all(
            """elements => elements.map(element => element.href)"""
        )
        before = len(ordered_links)
        for link in raw_links:
            canonical = link.split("?")[0].rstrip("/") + "/"
            if own_resource.match(canonical):
                ordered_links.setdefault(canonical, None)

        if len(ordered_links) == before:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if max_posts is not None and len(ordered_links) >= max_posts:
            break
        if stable_rounds >= 3 and ordered_links:
            break

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(900)

    return list(ordered_links)
