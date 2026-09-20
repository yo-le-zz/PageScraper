from pathlib import Path

import typer

from PageScrapper.scraper.browser import scrape_page
from PageScrapper.scraper.rebuilder import rebuild


app = typer.Typer(
    name="yolezz-webscraper",
    help="Récupère une page web et ses ressources localement.",
    no_args_is_help=True,
)


@app.command()
def scrape(
    url: str = typer.Argument(
        ...,
        help="URL de la page à récupérer.",
    ),
    output: Path = typer.Option(
        Path("output"),
        "--output",
        "-o",
        help="Dossier de sortie.",
    ),
    wait: float = typer.Option(
        2.0,
        "--wait",
        "-w",
        help="Temps d'attente après le chargement.",
    ),
    test: bool = typer.Option(
        False,
        "--test",
        help="Reconstruit une copie locale ouvrable avec index.html.",
    ),
):
    """Récupère une page web et ses ressources localement."""

    if not url.startswith(("http://", "https://")):
        typer.secho(
            "L'URL doit commencer par http:// ou https://",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    typer.secho(
        f"🌐 Analyse de {url}",
        fg=typer.colors.CYAN,
        bold=True,
    )

    try:
        result = scrape_page(
            url=url,
            output=output,
            wait=wait,
        )

        if test:
            typer.secho(
                "🔧 Reconstruction de la copie locale...",
                fg=typer.colors.YELLOW,
            )

            final_html = rebuild(
                output=output,
                base_url=url,
            )

            typer.secho(
                f"✓ Copie locale : {final_html}",
                fg=typer.colors.GREEN,
            )

    except Exception as exc:
        typer.secho(
            f"✗ Échec : {exc}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(1)

    typer.echo()

    typer.secho(
        "✓ Extraction terminée",
        fg=typer.colors.GREEN,
        bold=True,
    )

    typer.echo(f"  HTML       : {result.html}")
    typer.echo(f"  CSS        : {result.css_count} fichier(s)")
    typer.echo(f"  JavaScript : {result.js_count} fichier(s)")
    typer.echo(f"  Assets     : {result.asset_count} fichier(s)")

    if test:
        typer.echo("  Mode test  : activé")

    typer.echo(
        f"  Sortie     : {output.resolve()}"
    )


if __name__ == "__main__":
    app()