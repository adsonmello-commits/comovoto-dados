#!/usr/bin/env python3
"""Download and compact official TSE 2026 section results for non-presidential offices."""
from __future__ import annotations
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
import unicodedata
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PORTAL_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-2026"
SOURCE_TEMPLATE = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2026_{state}.zip"
EXPECTED_MUNICIPALITIES = {
    "AC":22,"AL":102,"AM":62,"AP":16,"BA":417,"CE":184,"DF":1,"ES":78,"GO":246,
    "MA":217,"MG":853,"MS":79,"MT":142,"PA":144,"PB":223,"PE":184,"PI":224,
    "PR":399,"RJ":92,"RN":167,"RO":52,"RR":15,"RS":497,"SC":295,"SE":75,"SP":645,"TO":139
}
OFFICE_NAMES = {
    "GOVERNADOR": "Governador",
    "SENADOR": "Senador",
    "DEPUTADO_FEDERAL": "Deputado federal",
    "DEPUTADO_ESTADUAL": "Deputado estadual",
    "DEPUTADO_DISTRITAL": "Deputado distrital"
}
INVALID_CODES = {"95", "96", "97", "98"}

def norm(value: str) -> str:
    plain = unicodedata.normalize("NFKD", (value or "").strip().lstrip("\ufeff").upper())
    return " ".join("".join(ch for ch in plain if not unicodedata.combining(ch)).split())

def cargo_code(value: str) -> str | None:
    text = norm(value)
    if "PRESIDENTE" in text:
        return None
    if "GOVERNADOR" in text:
        return "GOVERNADOR"
    if "SENADOR" in text:
        return "SENADOR"
    if "DEPUTADO FEDERAL" in text:
        return "DEPUTADO_FEDERAL"
    if "DEPUTADO ESTADUAL" in text:
        return "DEPUTADO_ESTADUAL"
    if "DEPUTADO DISTRITAL" in text:
        return "DEPUTADO_DISTRITAL"
    return None

def integer(value: str | None) -> int:
    try:
        return int((value or "0").strip())
    except ValueError:
        return 0

def import_state(state: str) -> None:
    source_url = SOURCE_TEMPLATE.format(state=state)
    temp_dir = Path(tempfile.mkdtemp(prefix=f"comovoto-cargos-{state.lower()}-"))
    archive_path = temp_dir / "source.zip"
    build_dir = Path(tempfile.mkdtemp(prefix=f".{state.lower()}-cargos-", dir=Path("data/2026")))
    digest = hashlib.sha256()
    archive_size = 0
    streams: dict[tuple[str, str], io.TextIOWrapper] = {}
    raw_files = []
    cities: dict[str, dict] = {}
    city_sections: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    state_turns: dict[str, set[str]] = {code: set() for code in OFFICE_NAMES}
    state_rows: Counter[str] = Counter()
    try:
        request = urllib.request.Request(source_url, headers={"User-Agent": "ComoVoto-data-import/2.0"})
        with urllib.request.urlopen(request, timeout=360) as response, archive_path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk)
                archive_size += len(chunk)
                output.write(chunk)

        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                raise RuntimeError(f"{state}: arquivo corrompido: {bad_member}")
            members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith((".csv", ".txt"))]
            if not members:
                raise RuntimeError(f"{state}: ZIP sem CSV/TXT")
            seen_offices: set[str] = set()
            for member in members:
                with archive.open(member) as binary, io.TextIOWrapper(binary, encoding="latin-1", newline="") as text:
                    reader = csv.DictReader(text, delimiter=";")
                    fields = {norm(field): field for field in (reader.fieldnames or [])}
                    required = ("SG_UF","CD_MUNICIPIO","NM_MUNICIPIO","DS_CARGO","NR_TURNO","NR_ZONA","NR_SECAO","NR_VOTAVEL","NM_VOTAVEL","QT_VOTOS")
                    missing = [field for field in required if field not in fields]
                    if missing:
                        raise RuntimeError(f"{state}: colunas ausentes em {member.filename}: {', '.join(missing)}")
                    for row in reader:
                        uf = (row.get(fields["SG_UF"]) or "").strip().upper()
                        if uf != state:
                            continue
                        office = cargo_code(row.get(fields["DS_CARGO"]) or "")
                        if office not in OFFICE_NAMES:
                            continue
                        turn = (row.get(fields["NR_TURNO"]) or "").strip()
                        city = (row.get(fields["CD_MUNICIPIO"]) or "").strip()
                        vote_code = (row.get(fields["NR_VOTAVEL"]) or "").strip()
                        zone = (row.get(fields["NR_ZONA"]) or "").strip()
                        section = (row.get(fields["NR_SECAO"]) or "").strip()
                        votes = integer(row.get(fields["QT_VOTOS"]))
                        if turn not in {"1","2"} or not city.isdigit() or not vote_code or not zone or not section or votes <= 0:
                            continue
                        city = city.zfill(5)
                        city_name = (row.get(fields["NM_MUNICIPIO"]) or "").strip()
                        candidate_name = (row.get(fields["NM_VOTAVEL"]) or "").strip()
                        party_field = fields.get("SG_PARTIDO")
                        party = (row.get(party_field) or "").strip() if party_field else ""
                        state_turns[office].add(turn)
                        seen_offices.add(office)
                        key = (city, office)
                        city_entry = cities.setdefault(city, {"id":city,"name":city_name,"uf":state,"offices":{}})
                        if not city_entry["name"] and city_name:
                            city_entry["name"] = city_name
                        city_office = city_entry["offices"].setdefault(office, {"turns":set(),"sections":{},"records":0})
                        city_office["turns"].add(turn)
                        city_office["sections"].setdefault(turn,set()).add((zone,section))
                        if key not in streams:
                            folder = build_dir / "municipalities" / city
                            folder.mkdir(parents=True, exist_ok=True)
                            raw = (folder / f"{office}.jsonl.gz").open("wb")
                            raw_files.append(raw)
                            compressed = gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0)
                            streams[key] = io.TextIOWrapper(compressed, encoding="utf-8", newline="\n")
                        # [turn,zone,section,local,candidate code,candidate label,party,votes]
                        local_field = fields.get("NR_LOCAL_VOTACAO")
                        local_code = (row.get(local_field) or "").strip() if local_field else ""
                        record = [turn,zone,section,local_code,vote_code,candidate_name,party,votes]
                        streams[key].write(json.dumps(record, ensure_ascii=False, separators=(",",":")) + "\n")
                        city_office["records"] += 1
                        state_rows[office] += 1
            for stream in streams.values():
                stream.close()
            for raw in raw_files:
                raw.close()

        expected_offices = {"GOVERNADOR","SENADOR","DEPUTADO_FEDERAL"}
        expected_offices.add("DEPUTADO_DISTRITAL" if state == "DF" else "DEPUTADO_ESTADUAL")
        missing_offices = expected_offices - seen_offices
        if missing_offices:
            raise RuntimeError(f"{state}: cargos esperados ausentes: {sorted(missing_offices)}")
        found = len(cities)
        expected = EXPECTED_MUNICIPALITIES[state]
        if found != expected:
            raise RuntimeError(f"{state}: esperados {expected} municípios com resultados; encontrados {found}")
        offices = {}
        for code in sorted(seen_offices):
            offices[code] = {"name":OFFICE_NAMES[code],"turns":sorted(state_turns[code]),"data_status":"complete" if "2" in state_turns[code] else "first_round"}
        municipality_list = []
        for code, city in cities.items():
            normalized = {"id":code,"name":city["name"],"uf":state,"offices":{}}
            for office, detail in city["offices"].items():
                file = f"municipalities/{code}/{office}.jsonl.gz"
                normalized["offices"][office] = {
                    "file":file,
                    "turns":sorted(detail["turns"]),
                    "sections_by_turn":{turn:len(sections) for turn,sections in sorted(detail["sections"].items())},
                    "records":detail["records"],
                    "file_size_bytes":(build_dir / file).stat().st_size
                }
            municipality_list.append(normalized)
        index = {
            "dataset":"Eleições 2026 — votação por seção para cargos estaduais e proporcionais",
            "uf":state,
            "source":source_url,
            "source_portal":PORTAL_URL,
            "municipality_count":found,
            "offices":offices,
            "municipalities":sorted(municipality_list,key=lambda item:item["name"])
        }
        (build_dir/"index.json").write_text(json.dumps(index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        manifest = {
            "dataset":index["dataset"],
            "scope":{"country":"Brasil","state":state,"municipalities":found},
            "source":source_url,
            "source_portal":PORTAL_URL,
            "license":"Creative Commons Attribution (CC BY)",
            "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
            "source_archive_size_bytes":archive_size,
            "source_archive_sha256":digest.hexdigest(),
            "source_archive_members":[m.filename for m in members],
            "office_turns":{code:sorted(turns) for code,turns in sorted(state_turns.items()) if turns},
            "office_rows":dict(sorted(state_rows.items())),
            "municipality_count":found,
            "partition_count":sum(len(city["offices"]) for city in cities.values())
        }
        (build_dir/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        out_dir = Path("data/2026") / state
        if out_dir.exists():
            shutil.rmtree(out_dir)
        build_dir.replace(out_dir)
        print(f"{state}: {found} municípios, {sum(state_rows.values()):,} registros compactos; turnos {manifest['office_turns']}.")
    finally:
        for stream in streams.values():
            if not stream.closed:
                stream.close()
        for raw in raw_files:
            if not raw.closed:
                raw.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, choices=sorted(EXPECTED_MUNICIPALITIES))
    args = parser.parse_args()
    import_state(args.state)

if __name__ == "__main__":
    main()
