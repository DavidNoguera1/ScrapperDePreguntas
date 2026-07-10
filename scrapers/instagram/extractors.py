import logging
from datetime import datetime


LOGGER = logging.getLogger(__name__)


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


def expand_comments(page):
    patterns = (
        "load more comments", "view more comments", "view all comments",
        "view all", "view replies", "load more replies",
        "cargar más comentarios", "ver más comentarios",
        "ver todos los comentarios", "ver todos", "ver respuestas",
        "ver más respuestas",
    )
    stable_rounds = 0
    previous_count = -1

    page.wait_for_timeout(2_000)

    for _ in range(30):
        current_count = page.locator('a[href*="/c/"] time').count()

        clicked = page.evaluate(
            """patterns => {
                const normalized = value => String(value || '')
                    .trim().toLocaleLowerCase();
                const candidates = Array.from(
                    document.querySelectorAll('[role="button"], button')
                );
                let clicks = 0;
                for (const element of candidates) {
                    if (clicks >= 12) break;
                    const svgLabels = Array.from(element.querySelectorAll('svg'))
                        .map(svg => svg.getAttribute('aria-label') || '')
                        .join(' ');
                    const label = normalized(
                        `${element.innerText || ''} ${element.getAttribute('aria-label') || ''} ${svgLabels}`
                    );
                    if (patterns.some(pattern => label.includes(pattern))) {
                        element.click();
                        clicks += 1;
                    }
                }
                return clicks;
            }""",
            patterns,
        )

        page.evaluate(
            """() => {
                const links = document.querySelectorAll('a[href*="/c/"]');
                if (!links.length) return;
                for (const link of links) {
                    let el = link.parentElement;
                    for (let i = 0; el && i < 20; i++) {
                        const style = window.getComputedStyle(el);
                        const overflow = (style.overflowY + style.overflow);
                        if (overflow.includes('auto') || overflow.includes('scroll')) {
                            el.scrollTop = el.scrollHeight;
                            return;
                        }
                        el = el.parentElement;
                    }
                }
                const container = document.querySelector('article') ||
                                  document.querySelector('[role="dialog"]');
                if (container) container.scrollTop = container.scrollHeight;
            }"""
        )

        page.wait_for_timeout(1000)

        if current_count > 0 and current_count == previous_count and clicked == 0:
            stable_rounds += 1
        else:
            stable_rounds = 0
        if stable_rounds >= 3:
            break

        previous_count = current_count


def extract_comments(page):
    return page.evaluate(
        """() => {
            const output = [];
            const seen = new Set();
            const timeNodes = Array.from(
                document.querySelectorAll('a[href*="/c/"] time')
            );

            for (const time of timeNodes) {
                const permalink = time.closest('a[href*="/c/"]');
                if (!permalink) continue;
                const href = permalink.href || permalink.getAttribute('href') || '';
                if (seen.has(href)) continue;

                let node = permalink.parentElement;
                let text = '';
                let author = '';
                const timeText = (time.innerText || '').trim();
                const metadataPattern = /^(?:\\d+\\s*(?:s|sec|m|min|h|hr|d|day|w|wk|sem|mes|mo|y|yr)(?:\\s*[·•]\\s*(?:edited|editado))?|\\d+\\s*(?:like|likes|me gusta))$/i;
                const uiNoise = new Set([
                    'follow', 'seguir', 'reply', 'responder', 'like',
                    'me gusta', 'see translation', 'ver traducción',
                    'view replies', 'ver respuestas', 'edited', 'editado'
                ]);

                for (let level = 0; node && level < 7; level++, node = node.parentElement) {
                    const profileLink = Array.from(node.querySelectorAll('a[href]'))
                        .find(link => {
                            const path = link.getAttribute('href') || '';
                            return /^\\/[A-Za-z0-9._]+\\/$/.test(path);
                        });
                    if (profileLink) author = (profileLink.innerText || '').trim();

                    const candidates = Array.from(
                        node.querySelectorAll('span[dir="auto"]')
                    ).filter(span => {
                        if (span.closest('a')) return false;
                        if (span.querySelector('span[dir="auto"]')) return false;
                        const value = (span.innerText || '').trim();
                        const normalized = value.toLocaleLowerCase();
                        return value
                            && value !== author
                            && value !== timeText
                            && !metadataPattern.test(value)
                            && !uiNoise.has(normalized);
                    });

                    if (candidates.length) {
                        text = (candidates[candidates.length - 1].innerText || '').trim();
                        break;
                    }
                }

                if (!text) continue;
                seen.add(href);
                output.push({
                    id: href,
                    text,
                    author,
                    datetime: time.getAttribute('datetime') || '',
                });
            }
            return output;
        }"""
    )
