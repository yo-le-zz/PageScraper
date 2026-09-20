from pathlib import Path
from urllib.parse import urlparse

import shutil
from playwright.sync_api import Browser, Page, sync_playwright

from .extractor import extract_page
from .models import ScrapeResult


def create_browser(playwright):
    chromium_path = (
        shutil.which("chromium")
        or shutil.which("chromium-browser")
        or shutil.which("google-chrome")
        or shutil.which("google-chrome-stable")
    )

    if not chromium_path:
        raise RuntimeError(
            "Chromium introuvable. "
            "Installez Chromium avec : sudo apt install chromium"
        )

    return playwright.chromium.launch(
        executable_path=chromium_path,
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ],
    )


def configure_page(page: Page):
    page.set_default_timeout(30_000)

    page.set_extra_http_headers(
        {
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        }
    )


def scrape_page(
    url: str,
    output: Path,
    wait: float,
) -> ScrapeResult:
    output.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser: Browser = create_browser(playwright)

        try:
            page = browser.new_page(
                viewport={
                    "width": 1920,
                    "height": 1080,
                },
                device_scale_factor=1,
            )

            configure_page(page)

            response = page.goto(
                url,
                wait_until="networkidle",
            )

            if response is None:
                raise RuntimeError(
                    "Le navigateur n'a reçu aucune réponse."
                )

            if response.status >= 400:
                raise RuntimeError(
                    f"Le serveur a répondu avec HTTP {response.status}."
                )

            # Laisse aux frameworks JS le temps de terminer leur rendu.
            if wait > 0:
                page.wait_for_timeout(int(wait * 1000))

            # Petit scroll pour déclencher certains lazy-load.
            page.evaluate(
                """
                async () => {
                    const distance = 500;
                    let position = 0;

                    while (position < document.body.scrollHeight) {
                        window.scrollTo(0, position);
                        position += distance;
                        await new Promise(r => setTimeout(r, 50));
                    }

                    window.scrollTo(0, 0);
                }
                """
            )

            page.wait_for_timeout(300)

            result = extract_page(
                page=page,
                output=output,
                base_url=url,
            )

            return result

        finally:
            browser.close()