#!/usr/bin/env python3
"""Import presidential section results from the official TSE national archive."""
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

SOURCE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_BR.zip"
PORTAL_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-2026"
STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins"
}
STATE_CODES = set(STATE_NAMES)
OUT_BASE = Path("data/2026/presidencia")
INVALID = {"95", "96", "97", "98"}


def norm(value: str) -> str:
    return (value or "").strip().lstrip("\ufeff").upper()


def to_int(value: str | None) -> int:
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
    cities: dict[str, dict[str, dict]] = {uf: {} for uf in STATE_NAMES}
    sections: dict[tuple[str, str], set[tuple[str, str, str]]] = {}
    candidates: dict[str, dict] = {}
    turns: dict[str, set[str]] = {uf: set() for uf in STATE_NAMES}
    rows_total: Counter[str] = Counter()

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
                    fields = {norm(field): field for field in (reader.fieldnames or [])}
                    required = ("SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_TURNO", "NR_ZONA", "NR_SECAO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS")
                    missing = [field for field in required if field not in fields]
                    if missing:
                        raise RuntimeError(f"Colunas ausentes em {member.filename}: {', '.join(missing)}")
                    cargo_field = fields.get("DS_CARGO")
                    for row in reader:
                        state = (row.get(fields["SG_UF"]) or "").strip().upper()
                        if state not in STATE_CODES:
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
                        votes = to_int(row.get(fields["QT_VOTOS"]))
                        if turn not in {"1", "2"} or not candidate:
                            continue
                        turns[state].add(turn)
                        candidates.setdefault(candidate, {
                            "name": candidate_name,
                            "short": candidate_name,
                            "color": "#d64751" if candidate == "13" else "#3478d0" if candidate == "22" else "#71818a"
                        })
                        key = (state, code)
                        if key not in streams:
                            folder = OUT_BASE / state / "municipalities"
                            folder.mkdir(parents=True, exist_ok=True)
                            path = folder / f"{code}.jsonl.gz"
                            raw = path.open("wb")
                            raw_files.append(raw)
                            compressed = gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0)
                            streams[key] = io.TextIOWrapper(compressed, encoding="utf-8", newline="\n")
                            cities[state][code] = {
                                "id": code, "name": name, "uf": state,
                                "file": f"municipalities/{code}.jsonl.gz",
                                "records": 0, "turns": {}
                            }
                            sections[key] = set()
                        city = cities[state][code]
                        if not city["name"] and name:
                            city["name"] = name
                        streams[key].write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                        city["records"] += 1
                        rows_total[state] += 1
                        values = city["turns"].setdefault(turn, {"votes": {}, "valid": 0, "turnout": 0})
                        values["votes"][candidate] = values["votes"].get(candidate, 0) + votes
                        values["turnout"] += votes
                        if candidate not in INVALID:
                            values["valid"] += votes
                        sections[key].add((turn, zone, section))
            for stream in streams.values():
                stream.close()
            for raw in raw_files:
                raw.close()

        for state in STATE_NAMES:
            found = len(cities[state])
            if found == 0:
                raise RuntimeError(f"{state}: nenhum município presidencial foi encontrado no arquivo nacional.")
            if "1" not in turns[state]:
                raise RuntimeError(f"{state}: o arquivo presidencial não trouxe o 1º turno.")
            complete = {"1", "2"}.issubset(turns[state])
            for (uf, code), section_rows in sections.items():
                if uf != state:
                    continue
                section_counts = Counter(turn for turn, _, _ in section_rows)
                city = cities[state][code]
                for turn in city["turns"]:
                    city["turns"][turn]["sections"] = section_counts[turn]
                city["sections"] = max(section_counts.values(), default=0)
                city["file_size_bytes"] = (OUT_BASE / state / city["file"]).stat().st_size
            index = {
                "dataset": "Presidente — votação por seção — Eleições 2026",
                "office": "Presidente da República",
                "uf": state, "state": STATE_NAMES[state], "source": SOURCE_URL,
                "municipality_count": found,
                "expected_turns": ["1", "2"], "turns": sorted(turns[state]),
                "data_status": "complete" if complete else "pending_tse_update",
                "candidates": candidates,
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
                "source_archive_size_bytes": archive_size, "source_archive_sha256": source_sha,
                "source_archive_members": [m.filename for m in members],
                "municipality_count": found, "expected_turns": ["1", "2"],
                "turns": sorted(turns[state]), "data_status": index["data_status"],
                "row_count": rows_total[state], "partition_count": found
            }
            (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{state}: {found} municípios, {rows_total[state]:,} registros presidenciais, turnos {sorted(turns[state])}.")
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
