#!/usr/bin/env python3
"""Download and validate the official TSE 2026 RS section-vote archive."""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_RS.zip"
OUT_DIR = Path("data/source/2026/RS")
ARCHIVE = OUT_DIR / "votacao_secao_2026_RS.zip"
MANIFEST = OUT_DIR / "manifest.json"
MAX_BYTES = 90 * 1024 * 1024


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    temp = ARCHIVE.with_suffix(".zip.part")
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "ComoVoto-data-import/1.0"},
    )
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=180) as response, temp.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise RuntimeError(
                    f"Arquivo tem mais de {MAX_BYTES // (1024 * 1024)} MiB; "
                    "não será gravado no Git comum."
                )
            digest.update(chunk)
            output.write(chunk)

    try:
        with zipfile.ZipFile(temp) as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise RuntimeError(f"Falha de integridade no arquivo interno: {bad_member}")
            members = [
                {"name": item.filename, "size_bytes": item.file_size}
                for item in archive.infolist()
                if not item.is_dir()
            ]
            if not members:
                raise RuntimeError("O ZIP oficial não contém arquivos.")
        os.replace(temp, ARCHIVE)
    except Exception:
        temp.unlink(missing_ok=True)
        raise

    manifest = {
        "dataset": "Resultados eleitorais 2026 — votação por seção",
        "scope": {"country": "Brasil", "state": "RS", "municipalities": "all"},
        "source": SOURCE_URL,
        "source_portal": "https://dadosabertos.tse.jus.br/dataset/resultados-2026",
        "license": "Creative Commons Attribution (CC BY)",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": ARCHIVE.name,
        "archive_size_bytes": size,
        "sha256": digest.hexdigest(),
        "zip_members": members,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Validado: {ARCHIVE} ({size:,} bytes; SHA-256 {digest.hexdigest()})")


if __name__ == "__main__":
    main()
