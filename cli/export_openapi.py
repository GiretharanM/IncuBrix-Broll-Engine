"""
IncuBrix B-roll Engine - OpenAPI 3.1 YAML Generator
---------------------------------------------------
Usage:
    python -m cli.export_openapi
    python -m cli.export_openapi --out ./openapi.yaml
"""

import sys
import yaml
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("incubrix.cli.openapi")

def export_openapi(output_path: str = "openapi.yaml"):
    try:
        import os
        os.environ.setdefault("ENVIRONMENT", "testing")
        os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
        from app.main import app
        schema = app.openapi()
        schema["openapi"] = "3.1.0"

        out_file = Path(output_path)
        with open(out_file, "w", encoding="utf-8") as f:
            yaml.dump(schema, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

        logger.info(f"Exported valid OpenAPI 3.1.0 schema to {out_file.resolve()} ({out_file.stat().st_size} bytes)")
        print(f"\n[OK] OpenAPI 3.1.0 schema generated at: {out_file.resolve()}\n")
    except Exception as e:
        logger.error(f"Failed to export OpenAPI schema: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Export running FastAPI OpenAPI 3.1 specification to YAML")
    parser.add_argument("--out", default="openapi.yaml", help="Destination path for openapi.yaml")
    args = parser.parse_args()
    export_openapi(args.out)

if __name__ == "__main__":
    main()
