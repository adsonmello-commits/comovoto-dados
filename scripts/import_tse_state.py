#!/usr/bin/env python3
"""Download and partition official TSE 2026 section-vote data by municipality."""
from __future__ import annotations

import argparse
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

PORTAL_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-2026"
EXPECTED_MUNICIPALITIES = {"RS": 497, "SC": 295, "PR": 399}
STATE_NAMES = {"RS": "Rio Grande do Sul", "SC": "Santa Catarina", "PR": "Paraná"}
SOURCE_TEMPLATE = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_{state}.zip"


def norm(value: str) -> str:
    return (value or "").strip().lstrip("\ufeff").upper()


def import_state(state: str) -> None:
    source_url = SOURCE_TEMPLATE.format(state=state)
    out_dir = Path("data/2026") / state
    municipality_dir = out_dir / "municipalities"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"comovoto-tse-{state.lower()}-"))
    archive_path = temp_dir / "source.zip"
    digest = hashlib.sha256()
    archive_size = 0
    request = urllib.request.Request(source_url, headers={"User-Agent": "ComoVoto-data-import/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=300) as response, archive_path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                archive_size += len(chunk)
                output.write(chunk)

        source_sha = digest.hexdigest()
        manifest_path = out_dir / "manifest.json"
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            if previous.get("source_archive_sha256") == source_sha and municipality_dir.exists():
                print(f"{state}: arquivo do TSE sem alterações; mantendo as partições atuais.")
                return

        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise RuntimeError(f"{state}: falha de integridade no arquivo {bad_member}")
            members = [
                item for item in archive.infolist()
                if not item.is_dir() and item.filename.lower().endswith((".csv", ".txt"))
            ]
            if not members:
                raise RuntimeError(f"{state}: ZIP oficial sem arquivo CSV ou TXT.")

            shutil.rmtree(municipality_dir, ignore_errors=True)
            municipality_dir.mkdir(parents=True, exist_ok=True)
            streams: dict[str, io.TextIOWrapper] = {}
            raw_files = []
            cities: dict[str, dict] = {}
            section_sets: dict[str, set[tuple[str, str, str]]] = {}
            turns_seen: set[str] = set()
            rows_total = 0
            try:
                for member in members:
                    with archive.open(member) as binary, io.TextIOWrapper(binary, encoding="latin-1", newline="") as text:
                        reader = csv.DictReader(text, delimiter=";")
                        fields = {norm(field): field for field in (reader.fieldnames or [])}
                        code_field = fields.get("CD_MUNICIPIO")
                        if not code_field:
                            raise RuntimeError(f"{state}: coluna CD_MUNICIPIO ausente em {member.filename}")
                        uf_field = fields.get("SG_UF")
                        name_field = fields.get("NM_MUNICIPIO")
                        turn_field = fields.get("NR_TURNO")
                        zone_field = fields.get("NR_ZONA")
                        section_field = fields.get("NR_SECAO")
                        for row in reader:
                            row_state = (row.get(uf_field) or "").strip().upper() if uf_field else state
                            if row_state and row_state != state:
                                continue
                            code = (row.get(code_field) or "").strip()
                            if not code.isdigit():
                                continue
                            code = code.zfill(5)
                            name = (row.get(name_field) or "").strip() if name_field else ""
                            turn = (row.get(turn_field) or "").strip() if turn_field else ""
                            if turn:
                                turns_seen.add(turn)
                            if code not in streams:
                                raw_path = municipality_dir / f"{code}.jsonl.gz"
                                raw_file = raw_path.open("wb")
                                raw_files.append(raw_file)
                                compressed = gzip.GzipFile(fileobj=raw_file, mode="wb", compresslevel=9, mtime=0)
                                streams[code] = io.TextIOWrapper(compressed, encoding="utf-8", newline="\n")
                                cities[code] = {
                                    "id": code,
                                    "name": name,
                                    "uf": state,
                                    "file": f"municipalities/{code}.jsonl.gz",
                                    "records": 0,
                                    "sections_by_turn": {},
                                }
                                section_sets[code] = set()
                            if not cities[code]["name"] and name:
                                cities[code]["name"] = name
                            streams[code].write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                            cities[code]["records"] += 1
                            rows_total += 1
                            if turn and zone_field and section_field:
                                zone = (row.get(zone_field) or "").strip()
                                section = (row.get(section_field) or "").strip()
                                section_sets[code].add((turn, zone, section))
            finally:
                for stream in streams.values():
                    stream.close()
                for raw_file in raw_files:
                    raw_file.close()

        expected = EXPECTED_MUNICIPALITIES[state]
        if len(cities) != expected:
            raise RuntimeError(f"{state}: esperados {expected} municípios; encontrados {len(cities)}.")
        if "1" not in turns_seen:
            raise RuntimeError(f"{state}: dados do 1º turno ausentes; encontrados {sorted(turns_seen)}.")

        data_complete = {"1", "2"}.issubset(turns_seen)
        for code, city in cities.items():
            counts = Counter(turn for turn, _, _ in section_sets[code])
            city["sections_by_turn"] = dict(sorted(counts.items()))
            city["file_size_bytes"] = (municipality_dir / f"{code}.jsonl.gz").stat().st_size

        index = {
            "dataset": "Resultados eleitorais 2026 — votação por seção",
            "uf": state,
            "state": STATE_NAMES[state],
            "source": source_url,
            "municipality_count": len(cities),
            "expected_turns": ["1", "2"],
            "turns": sorted(turns_seen),
            "data_status": "complete" if data_complete else "pending_tse_update",
            "municipalities": sorted(cities.values(), key=lambda item: item["name"]),
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        manifest = {
            "dataset": index["dataset"],
            "scope": {"country": "Brasil", "state": state, "municipalities": "all"},
            "source": source_url,
            "source_portal": PORTAL_URL,
            "license": "Creative Commons Attribution (CC BY)",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_archive_size_bytes": archive_size,
            "source_archive_sha256": source_sha,
            "source_archive_members": [item.filename for item in members],
            "municipality_count": len(cities),
            "expected_turns": ["1", "2"],
            "turns": sorted(turns_seen),
            "data_status": index["data_status"],
            "row_count": rows_total,
            "partition_count": len(cities),
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{state}: {len(cities)} municípios, {rows_total:,} registros, turnos {sorted(turns_seen)}.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, choices=sorted(EXPECTED_MUNICIPALITIES))
    args = parser.parse_args()
    import_state(args.state)


if __name__ == "__main__":
    main()
