"""Check the built website for pages that built but show something broken.

Run after `quarto render` (the publish workflow does this):  python .github/check_site.py
Fails when:
- a page shows a Python error, or an object like `<branca.element.Figure at 0x...>` instead of a map or chart
- a notebook post was committed without outputs (Quarto doesn't run notebooks, so the page would be empty)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROBLEMS = {
    "Python error": re.compile(r"Traceback \(most recent call last\)|cell-output-error"),
    "object shown as text instead of a map/chart": re.compile(r"&lt;[\w.]+(?: object)? at 0x[0-9a-fA-F]+&gt;"),
}


def check_pages() -> list[str]:
    errors = []
    for page in sorted((ROOT / "_site").rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        for problem, pattern in PROBLEMS.items():
            if match := pattern.search(html):
                errors.append(f"{page.relative_to(ROOT)}: {problem}: {match.group(0)}")
    return errors


def check_notebooks() -> list[str]:
    errors = []
    for nb_path in sorted(ROOT.rglob("*.ipynb")):
        rel = nb_path.relative_to(ROOT)
        if any(part.startswith(("_", ".")) for part in rel.parts):  # not published by Quarto
            continue
        code_cells = [c for c in json.loads(nb_path.read_text(encoding="utf-8"))["cells"] if c["cell_type"] == "code"]
        if code_cells and not any(c.get("outputs") for c in code_cells):
            errors.append(f"{rel}: notebook has no outputs. Run all cells and save before committing.")
    return errors


if __name__ == "__main__":
    if not (ROOT / "_site").is_dir():
        sys.exit("No _site/ folder. Run `quarto render` first.")
    errors = check_pages() + check_notebooks()
    for e in errors:
        print(f"::error::{e}")  # shown as an annotation on GitHub
    if errors:
        sys.exit(f"{len(errors)} problem(s) found on the website.")
    print("Website check passed.")
