"""Export the generated API contract without touching the database."""

import json
from pathlib import Path

from app.main import create_app


def main() -> None:
    schema = create_app().openapi()
    target = Path("docs/openapi.json")
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
