#!/usr/bin/env python3
"""Import presidential section results from the official TSE national archive."""
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
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip"
PORTAL_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-2026"
EXPECTED = {"RS": 497, "SC": 295, "PR": 399}
STATE_NAMES = {"RS": "Rio Grande do Sul", "SC": "Santa Catarina", "PR": "Paraná"}
OUT_BASE = Path("data/2026/presidencia")
INVALID = {"95", "96", "97", "98"}


def norm(value: str) -> str:
    return (value or "").strip().lstrip("\ufeff").upper()


def num(value: str | None) -> int:
    try:
        return int((value or "0").strip())
    except ValueError:
        return 0


def main() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="comovoto-tse-presidente-"))
    archive_path = temp_dir / "source.zip"
    digest = hashlib.sha256()
    archive_size = 0
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "ComoVoto-data-import/1.0"})
    streams: dict[tuple[str, str], io.TextIOWrapper] = {}
    raw_files = []
    cities: dict[str, dict[str, dict]] = {uf: {} for uf in EXPECTED}
    sections: dict[tuple[str, str], set[tuple[str, str, str]]] = defaultdict(set)
    candidate_names: dict[str, str] = {}
    turns_by_state: dict[str, set[str]] = {uf: set() for uf in EXPECTED}
    rows_by_state: Counter[str] = Counter()

    try:
        with urllib.request.urlopen(request, timeout=360) as response, archive_path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                archive_size += len(chunk)
                output.write(chunk)

        source_sha = digest.hexdigest()
        with zipfile.ZipFile(archive_path) as archive:
            members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith((".csv", ".txt"))]
            if not members:
                raise RuntimeError("O arquivo presidencial do TSE não contém CSV ou TXT.")

            for member in members:
                with archive.open(member) as binary, io.TextIOWrapper(binary, encoding="latin-1", newline="") as text:
                    reader = csv.DictReader(text, delimiter=";")
                    fields = {norm(f): f for f in (reader.fieldnames or [])}
                    required = ("SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_TURNO", "NR_ZONA", "NR_SECAO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS")
                    missing = [name for name in required if name not in fields]
                    if missing:
                        raise RuntimeError(f"Colunas ausentes em {member.filename}: {', '.join(missing)}")
                    cargo_field = fields.get("DS_CARGO")
                    for row in reader:
                        state = (row.get(fields["SG_UF"]) or "").strip().upper()
                        if state not in EXPECTED:
                            continue
                        if cargo_field and "PRESIDENTE" not in (row.get(cargo_field) or "").upper():
                            continue
                        code = (row.get(fields["CD_MUNICIPIO"]) or "").strip()
                        if not code.isdigit():
                            continue
                        code = code.zfill(5)
                        name = (row.get(fields["NM_MUNICIPIO"]) or "").strip()
                        turn = (row.get(fields["NR_TURNO"]) or "").strip()
                        zone = (row.get(fields["NR_ZONA"]) or "").strip()
                        section = (row.get(fields["NR_SECAO"]) or "").strip()
                        candidate = (row.get(fields["NR_VOTAVEL"]) or "").strip()
                        candidate_name = (row.get(fields["NM_VOTAVEL"]) or "").strip()
                        votes = num(row.get(fields["QT_VOTOS"]))
                        if turn not in {"1", "2"} or not candidate:
                            continue
                        turns_by_state[state].add(turn)
                        candidate_names.setdefault(candidate, candidate_name)
                        key = (state, code)
                        if key not in streams:
                            out_dir = OUT_BASE / state / "municipalities"
                            out_dir.mkdir(parents=True, exist_ok=True)
                            path = out_dir / f"{code}.jsonl.gz"
                            raw = path.open("wb")
                            raw_files.append(raw)
                            compressed = gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0)
                            streams[key] = io.TextIOWrapper(compressed, encoding="utf-8", newline="\n")
                            cities[state][code] = {
                                "id": code, "name": name, "uf": state,
                                "file": f"municipalities/{code}.jsonl.gz",
                                "records": 0, "turns": {}
                            }
                        city = cities[state][code]
                        if not city["name"] and name:
                            city["name"] = name
                        streams[key].write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                        city["records"] += 1
                        rows_by_state[state] += 1
                        turn_data = city["turns"].setdefault(turn, {"votes": {}, "valid": 0, "turnout": 0})
                        turn_data["votes"][candidate] = turn_data["votes"].get(candidate, 0) + votes
                        turn_data["turnout"] += votes
                        if candidate not in INVALID:
                            turn_data["valid"] += votes
                        sections[key].add((turn, zone, section))
            for stream in streams.values():
                stream.close()
            for raw in raw_files:
                raw.close()

        for state, expected_count in EXPECTED.items():
            found = len(cities[state])
            if found != expected_count:
                raise RuntimeError(f"{state}: esperados {expected_count} municípios; encontrados {found}.")
            if "1" not in turns_by_state[state]:
                raise RuntimeError(f"{state}: o arquivo presidencial não trouxe o 1º turno.")
            for code, city in cities[state].items():
                by_turn = Counter(turn for turn, _, _ in sections[(state, code)])
                for turn, data in city["turns"].items():
                    data["sections"] = by_turn[turn]
                path = OUT_BASE / state / city["file"]
                city["file_size_bytes"] = path.stat().st_size

            complete = {"1", "2"}.issubset(turns_by_state[state])
            index = {
                "dataset": "Presidente — votação por seção — Eleições 2026",
                "office": "Presidente da República",
                "uf": state, "state": STATE_NAMES[state],
                "source": SOURCE_URL,
                "municipality_count": found,
                "expected_turns": ["1", "2"],
                "turns": sorted(turns_by_state[state]),
                "data_status": "complete" if complete else "pending_tse_update",
                "candidates": {
                    code: {"name": name, "short": name, "color": "#d64751" if code == "13" else "#3478d0" if code == "22" else "#71818a"}
                    for code, name in sorted(candidate_names.items())
                },
                "municipalities": sorted(cities[state].values(), key=lambda item: item["name"])
            }
            out_dir = OUT_BASE / state
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            manifest = {
                "dataset": index["dataset"], "office": index["office"],
                "scope": {"country": "Brasil", "state": state, "municipalities": "all"},
                "source": SOURCE_URL, "source_portal": PORTAL_URL,
                "license": "Creative Commons Attribution (CC BY)",
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_archive_size_bytes": archive_size,
                "source_archive_sha256": source_sha,
                "source_archive_members": [m.filename for m in members],
                "municipality_count": found,
                "expected_turns": ["1", "2"], "turns": sorted(turns_by_state[state]),
                "data_status": index["data_status"],
                "row_count": rows_by_state[state],
                "partition_count": found
            }
            (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{state}: {found} municípios, {rows_by_state[state]:,} registros presidenciais, turnos {sorted(turns_by_state[state])}.")
    finally:
        for stream in streams.values():
            if not stream.closed:
                stream.close()
        for raw in raw_files:
            if not raw.closed:
                raw.close()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
