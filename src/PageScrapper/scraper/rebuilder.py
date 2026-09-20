import re
from pathlib import Path
from urllib.parse import urljoin


URL_PATTERN = re.compile(
    r"""(?P<quote>["'])(?P<url>[^"']+)(?P=quote)"""
)


def normalize_url(value: str, base_url: str) -> str:
    """Transforme une URL relative en URL absolue."""

    if value.startswith(("data:", "blob:", "#", "javascript:")):
        return value

    return urljoin(base_url, value)


def build_resource_map(output: Path) -> dict[str, str]:
    """
    Construit une correspondance URL -> fichier local.

    Les fichiers possèdent actuellement leur hash dans leur nom.
    Cette fonction permet de retrouver les ressources à partir
    des métadonnées enregistrées par l'extracteur.
    """

    mapping_file = output / ".resource-map"

    if not mapping_file.exists():
        return {}

    mapping: dict[str, str] = {}

    for line in mapping_file.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        try:
            url, path = line.split("\t", 1)
        except ValueError:
            continue

        mapping[url] = path

    return mapping


def rewrite_css(
    css: str,
    source_url: str,
    output: Path,
    resource_map: dict[str, str],
) -> str:
    """Réécrit les url(...) présentes dans un CSS."""

    pattern = re.compile(
        r"""url\(\s*(['"]?)(.*?)\1\s*\)""",
        re.IGNORECASE,
    )

    def replace(match):
        original = match.group(2)

        if original.startswith(
            ("data:", "blob:", "#")
        ):
            return match.group(0)

        absolute = normalize_url(
            original,
            source_url,
        )

        local = resource_map.get(absolute)

        if not local:
            return match.group(0)

        return f'url("{local}")'

    return pattern.sub(
        replace,
        css,
    )


def rewrite_html(
    html: str,
    base_url: str,
    resource_map: dict[str, str],
) -> str:
    """Réécrit les URLs de ressources dans le HTML."""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    attributes = [
        "src",
        "href",
        "poster",
        "action",
        "data-src",
    ]

    for tag in soup.find_all(True):
        for attribute in attributes:
            value = tag.get(attribute)

            if not value:
                continue

            if value.startswith(
                ("data:", "blob:", "#", "javascript:")
            ):
                continue

            absolute = normalize_url(
                value,
                base_url,
            )

            local = resource_map.get(absolute)

            if local:
                tag[attribute] = local

        # srcset
        srcset = tag.get("srcset")

        if srcset:
            entries = []

            for entry in srcset.split(","):
                parts = entry.strip().split()

                if not parts:
                    continue

                original = parts[0]

                absolute = normalize_url(
                    original,
                    base_url,
                )

                local = resource_map.get(absolute)

                if local:
                    parts[0] = local

                entries.append(
                    " ".join(parts)
                )

            tag["srcset"] = ", ".join(entries)

    return str(soup)


def rebuild(
    output: Path,
    base_url: str,
) -> Path:
    """
    Reconstruit une copie locale exploitable.

    Le HTML final est placé directement à la racine
    du dossier output.
    """

    resource_map = build_resource_map(output)

    source_html = (
        output
        / "html"
        / "index.html"
    )

    if not source_html.exists():
        raise FileNotFoundError(
            f"HTML introuvable : {source_html}"
        )

    html = source_html.read_text(
        encoding="utf-8"
    )

    html = rewrite_html(
        html,
        base_url,
        resource_map,
    )

    # Réécriture des CSS.
    css_dir = output / "css"

    if css_dir.exists():
        for css_file in css_dir.glob("*.css"):
            css = css_file.read_text(
                encoding="utf-8",
                errors="replace",
            )

            source_url = resource_map.get(
                f"css-file:{css_file.name}",
                base_url,
            )

            css = rewrite_css(
                css,
                source_url,
                output,
                resource_map,
            )

            css_file.write_text(
                css,
                encoding="utf-8",
            )

    # HTML final à la racine.
    final_html = output / "index.html"

    final_html.write_text(
        html,
        encoding="utf-8",
    )

    return final_html