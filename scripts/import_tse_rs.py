#!/usr/bin/env python3
"""Import the official TSE 2026 RS section-vote archive as municipality files."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_RS.zip"
PORTAL_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-2026"
OUT_DIR = Path("data/2026/RS")
MUNICIPALITY_DIR = OUT_DIR / "municipalities"
EXPECTED_MUNICIPALITIES = 497


def norm(value: str) -> str:
    return (value or "").strip().lstrip("\ufeff").upper()


def main() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="comovoto-tse-rs-"))
    archive_path = temp_dir / "source.zip"
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "ComoVoto-data-import/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=240) as response, archive_path.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
                out.write(chunk)

        with zipfile.ZipFile(archive_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"Falha de integridade no membro {bad}")
            members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith((".csv", ".txt"))]
            if not members:
                raise RuntimeError("O ZIP oficial não contém CSV ou TXT.")

            shutil.rmtree(MUNICIPALITY_DIR, ignore_errors=True)
            MUNICIPALITY_DIR.mkdir(parents=True, exist_ok=True)
            streams: dict[str, io.TextIOWrapper] = {}
            cities: dict[str, dict] = {}
            section_sets: dict[str, set[tuple[str, str, str]]] = {}
            turns_seen: set[str] = set()
            rows_total = 0
            try:
                for member in members:
                    with archive.open(member) as binary, io.TextIOWrapper(binary, encoding="latin-1", newline="") as text:
                        reader = csv.DictReader(text, delimiter=";")
                        fields = {norm(f): f for f in (reader.fieldnames or [])}
                        code_f = fields.get("CD_MUNICIPIO")
                        if not code_f:
                            raise RuntimeError(f"Coluna CD_MUNICIPIO não encontrada em {member.filename}")
                        uf_f = fields.get("SG_UF")
                        name_f = fields.get("NM_MUNICIPIO")
                        turn_f = fields.get("NR_TURNO")
                        zone_f = fields.get("NR_ZONA")
                        section_f = fields.get("NR_SECAO")
                        for row in reader:
                            if uf_f and (row.get(uf_f) or "").strip().upper() not in ("", "RS"):
                                continue
                            code = (row.get(code_f) or "").strip()
                            if not code.isdigit():
                                continue
                            code = code.zfill(5)
                            name = (row.get(name_f) or "").strip() if name_f else ""
                            turn = (row.get(turn_f) or "").strip() if turn_f else ""
                            turns_seen.add(turn)
                            if code not in streams:
                                raw_path = MUNICIPALITY_DIR / f"{code}.jsonl.gz"
                                raw_file = raw_path.open("wb")
                                compressed = gzip.GzipFile(fileobj=raw_file, mode="wb", compresslevel=9, mtime=0)
                                streams[code] = io.TextIOWrapper(compressed, encoding="utf-8", newline="\n")
                                cities[code] = {
                                    "id": code, "name": name, "uf": "RS",
                                    "file": f"municipalities/{code}.jsonl.gz",
                                    "records": 0, "sections_by_turn": {}
                                }
                                section_sets[code] = set()
                            if not cities[code]["name"] and name:
                                cities[code]["name"] = name
                            streams[code].write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                            cities[code]["records"] += 1
                            rows_total += 1
                            if turn and zone_f and section_f:
                                section_sets[code].add((turn, (row.get(zone_f) or "").strip(), (row.get(section_f) or "").strip()))
            finally:
                for stream in streams.values():
                    stream.close()

        if len(cities) != EXPECTED_MUNICIPALITIES:
            raise RuntimeError(f"Esperados 497 municípios do RS; encontrados {len(cities)}.")
        if not {"1", "2"}.issubset(turns_seen):
            raise RuntimeError(f"Esperados dados dos dois turnos; encontrados {sorted(turns_seen)}")
        for code, city in cities.items():
            counts = Counter(turn for turn, _, _ in section_sets[code])
            city["sections_by_turn"] = dict(sorted(counts.items()))
            city["file_size_bytes"] = (MUNICIPALITY_DIR / f"{code}.jsonl.gz").stat().st_size

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        index = {
            "dataset": "Resultados eleitorais 2026 — votação por seção",
            "uf": "RS", "state": "Rio Grande do Sul",
            "source": SOURCE_URL, "municipality_count": len(cities),
            "turns": sorted(turns_seen),
            "municipalities": sorted(cities.values(), key=lambda item: item["name"])
        }
        (OUT_DIR / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest = {
            "dataset": index["dataset"],
            "scope": {"country": "Brasil", "state": "RS", "municipalities": "all"},
            "source": SOURCE_URL, "source_portal": PORTAL_URL,
            "license": "Creative Commons Attribution (CC BY)",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_archive_size_bytes": size, "source_archive_sha256": digest.hexdigest(),
            "source_archive_members": [m.filename for m in members],
            "municipality_count": len(cities), "turns": sorted(turns_seen),
            "row_count": rows_total, "partition_count": len(cities)
        }
        (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Importação validada: {len(cities)} municípios, {rows_total:,} linhas, turnos {sorted(turns_seen)}.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
