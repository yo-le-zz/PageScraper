from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScrapeResult:
    html: Path
    css_count: int
    js_count: int
    asset_count: int