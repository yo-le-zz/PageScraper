from pathlib import Path
from urllib.parse import urlparse

import hashlib
import re

from playwright.sync_api import Page

from .models import ScrapeResult


RESOURCE_DIRS = {
    "css": "css",
    "js": "javascript",
    "image": "assets/images",
    "font": "assets/fonts",
    "media": "assets/media",
    "other": "assets/other",
}


def safe_filename(url: str, fallback: str) -> str:
    parsed = urlparse(url)

    name = Path(parsed.path).name

    if not name:
        name = fallback

    name = re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        name,
    )

    digest = hashlib.sha256(
        url.encode("utf-8")
    ).hexdigest()[:10]

    path = Path(name)

    return (
        f"{path.stem}_{digest}{path.suffix}"
    )


def resource_type(
    url: str,
    content_type: str,
) -> str:
    content_type = content_type.lower()

    if "text/css" in content_type:
        return "css"

    if (
        "javascript" in content_type
        or "ecmascript" in content_type
    ):
        return "js"

    if content_type.startswith("image/"):
        return "image"

    if content_type.startswith("font/"):
        return "font"

    if (
        content_type.startswith("audio/")
        or content_type.startswith("video/")
    ):
        return "media"

    extension = Path(
        urlparse(url).path
    ).suffix.lower()

    if extension == ".css":
        return "css"

    if extension in {
        ".js",
        ".mjs",
        ".cjs",
    }:
        return "js"

    if extension in {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".avif",
        ".bmp",
    }:
        return "image"

    if extension in {
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
    }:
        return "font"

    if extension in {
        ".mp3",
        ".wav",
        ".ogg",
        ".mp4",
        ".webm",
        ".mov",
    }:
        return "media"

    return "other"


def save_resource(
    output: Path,
    url: str,
    content_type: str,
    body: bytes,
    counters: dict[str, int],
    resource_map: dict[str, str],
) -> Path:
    kind = resource_type(
        url,
        content_type,
    )

    directory = (
        output / RESOURCE_DIRS[kind]
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    counters[kind] = (
        counters.get(kind, 0) + 1
    )

    filename = safe_filename(
        url,
        f"resource_{counters[kind]}",
    )

    path = directory / filename

    path.write_bytes(body)

    # URL absolue -> chemin relatif local
    resource_map[url] = (
        path.relative_to(output)
        .as_posix()
    )

    return path


def write_resource_map(
    output: Path,
    resource_map: dict[str, str],
):
    mapping_file = (
        output / ".resource-map"
    )

    lines = [
        f"{url}\t{local}"
        for url, local
        in sorted(resource_map.items())
    ]

    mapping_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def extract_page(
    page: Page,
    output: Path,
    base_url: str,
) -> ScrapeResult:

    counters: dict[str, int] = {}
    captured: dict[
        str,
        tuple[str, bytes],
    ] = {}

    resource_map: dict[str, str] = {}

    # ---------------------------------------------------------
    # Capture réseau
    # ---------------------------------------------------------

    def handle_response(response):
        try:
            request = response.request

            if request.resource_type not in {
                "stylesheet",
                "script",
                "image",
                "font",
                "media",
                "fetch",
                "xhr",
            }:
                return

            url = response.url

            if url in captured:
                return

            content_type = response.headers.get(
                "content-type",
                "",
            )

            body = response.body()

            captured[url] = (
                content_type,
                body,
            )

        except Exception:
            pass

    page.on(
        "response",
        handle_response,
    )

    # ---------------------------------------------------------
    # CSS
    # ---------------------------------------------------------

    stylesheets = page.evaluate(
        """
        () => Array.from(document.styleSheets).map(sheet => ({
            href: sheet.href,
            cssRules: (() => {
                try {
                    return Array.from(sheet.cssRules)
                        .map(rule => rule.cssText)
                        .join("\\n");
                } catch {
                    return "";
                }
            })()
        }))
        """
    )

    css_dir = output / "css"

    css_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    css_count = 0

    for stylesheet in stylesheets:
        css = stylesheet.get(
            "cssRules",
            "",
        )

        href = stylesheet.get(
            "href"
        )

        if not css:
            continue

        if href:
            filename = safe_filename(
                href,
                f"stylesheet_{css_count}",
            )

            path = (
                css_dir / filename
            )

            path.write_text(
                css,
                encoding="utf-8",
            )

            # IMPORTANT :
            # on associe bien l'URL distante
            # au fichier CSS local.
            resource_map[href] = (
                path.relative_to(output)
                .as_posix()
            )

        else:
            filename = (
                f"inline_{css_count}.css"
            )

            path = (
                css_dir / filename
            )

            path.write_text(
                css,
                encoding="utf-8",
            )

        css_count += 1

    # ---------------------------------------------------------
    # Ressources présentes dans le DOM
    # ---------------------------------------------------------

    resources = page.evaluate(
        r"""
        () => {
            const urls = new Set();
    
            document
                .querySelectorAll("[src]")
                .forEach(el => {
                    if (el.src) {
                        urls.add(el.src);
                    }
                });
    
            document
                .querySelectorAll("[href]")
                .forEach(el => {
                    if (el.href) {
                        urls.add(el.href);
                    }
                });
    
            document
                .querySelectorAll("[srcset]")
                .forEach(el => {
                    const srcset =
                        el.getAttribute("srcset");
    
                    if (!srcset) {
                        return;
                    }
    
                    srcset
                        .split(",")
                        .forEach(part => {
                            const url =
                                part
                                    .trim()
                                    .split(/\s+/)[0];
    
                            if (url) {
                                urls.add(url);
                            }
                        });
                });
    
            document
                .querySelectorAll("[poster]")
                .forEach(el => {
                    if (el.poster) {
                        urls.add(el.poster);
                    }
                });
    
            return Array.from(urls);
        }
        """
    )

    # ---------------------------------------------------------
    # Téléchargement des ressources DOM
    # ---------------------------------------------------------

    for url in resources:

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            continue

        if url in captured:
            continue

        try:
            response = page.request.get(
                url,
                timeout=30_000,
            )

            if not response.ok:
                continue

            content_type = (
                response.headers.get(
                    "content-type",
                    "",
                )
            )

            body = response.body()

            captured[url] = (
                content_type,
                body,
            )

        except Exception:
            continue

    # ---------------------------------------------------------
    # Sauvegarde des ressources
    # ---------------------------------------------------------

    js_count = 0
    asset_count = 0

    for (
        url,
        (
            content_type,
            body,
        ),
    ) in captured.items():

        kind = resource_type(
            url,
            content_type,
        )

        if kind == "css":
            # Déjà traité par document.styleSheets
            continue

        path = save_resource(
            output=output,
            url=url,
            content_type=content_type,
            body=body,
            counters=counters,
            resource_map=resource_map,
        )

        if kind == "js":
            js_count += 1
        else:
            asset_count += 1

    # ---------------------------------------------------------
    # Sauvegarde du mapping
    # ---------------------------------------------------------

    write_resource_map(
        output,
        resource_map,
    )

    # ---------------------------------------------------------
    # HTML original
    # ---------------------------------------------------------

    html = page.content()

    html_dir = output / "html"

    html_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    html_path = (
        html_dir / "index.html"
    )

    html_path.write_text(
        html,
        encoding="utf-8",
    )

    return ScrapeResult(
        html=html_path,
        css_count=css_count,
        js_count=js_count,
        asset_count=asset_count,
    )