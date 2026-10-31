#!/usr/bin/env python3
"""Import official TSE 2024 municipal results by section into compact city partitions."""
from __future__ import annotations
import csv, gzip, hashlib, io, json, os, shutil, tempfile, unicodedata, urllib.request, zipfile
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PORTAL_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-2024"
SOURCE_TEMPLATE = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2024_{state}.zip"
STATES = ("AC","AL","AM","AP","BA","CE","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO")
OFFICE_NAMES = {"PREFEITO":"Prefeito","VEREADOR":"Vereador"}
INVALID_CODES = {"95","96","97","98","99"}

def norm(value: str) -> str:
    plain = unicodedata.normalize("NFKD", (value or "").strip().lstrip("\ufeff").upper())
    return " ".join("".join(ch for ch in plain if not unicodedata.combining(ch)).split())

def integer(value: str | None) -> int:
    try: return int(float((value or "0").replace(",", ".")))
    except (ValueError, TypeError): return 0

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True, choices=STATES)
    args = parser.parse_args()
    import_state(args.state)

def import_state(state: str) -> None:
    source_url = SOURCE_TEMPLATE.format(state=state)
    temp_dir = Path(tempfile.mkdtemp(prefix=f"tse2024-{state.lower()}-"))
    build_dir = temp_dir / "state"
    build_dir.mkdir()
    archive_path = temp_dir / "source.zip"
    digest = hashlib.sha256()
    archive_size = 0
    streams: OrderedDict[tuple[str,str], io.TextIOWrapper] = OrderedDict()
    raw_handles: dict[tuple[str,str], object] = {}
    cities = {}
    state_turns = defaultdict(set)
    state_rows = defaultdict(int)
    try:
        request = urllib.request.Request(source_url, headers={"User-Agent":"com-o-voto-data-builder/1.0"})
        with urllib.request.urlopen(request, timeout=180) as response, archive_path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                digest.update(chunk); archive_size += len(chunk); output.write(chunk)
        with zipfile.ZipFile(archive_path) as archive:
            bad_member = archive.testzip()
            if bad_member: raise RuntimeError(f"{state}: ZIP corrompido: {bad_member}")
            members = [m for m in archive.infolist() if not m.is_dir() and m.filename.lower().endswith((".csv",".txt"))]
            if not members: raise RuntimeError(f"{state}: ZIP sem arquivo CSV/TXT")
            seen_offices = set()
            for member in members:
                with archive.open(member) as binary, io.TextIOWrapper(binary, encoding="latin-1", newline="") as text:
                    reader = csv.DictReader(text, delimiter=";")
                    fields = {norm(field):field for field in (reader.fieldnames or [])}
                    required = ("SG_UF","CD_MUNICIPIO","NM_MUNICIPIO","DS_CARGO","NR_TURNO","NR_ZONA","NR_SECAO","NR_VOTAVEL","NM_VOTAVEL","QT_VOTOS")
                    missing = [field for field in required if field not in fields]
                    if missing: raise RuntimeError(f"{state}: campos ausentes em {member.filename}: {', '.join(missing)}")
                    for row in reader:
                        if (row.get(fields["SG_UF"]) or "").strip().upper() != state: continue
                        cargo = norm(row.get(fields["DS_CARGO"]) or "")
                        office = "PREFEITO" if "PREFEITO" in cargo else ("VEREADOR" if "VEREADOR" in cargo else None)
                        if office not in OFFICE_NAMES: continue
                        turn = (row.get(fields["NR_TURNO"]) or "").strip()
                        city = (row.get(fields["CD_MUNICIPIO"]) or "").strip()
                        vote_code = (row.get(fields["NR_VOTAVEL"]) or "").strip()
                        zone = (row.get(fields["NR_ZONA"]) or "").strip()
                        section = (row.get(fields["NR_SECAO"]) or "").strip()
                        votes = integer(row.get(fields["QT_VOTOS"]))
                        if turn not in {"1","2"} or not city.isdigit() or not vote_code or not zone or not section or votes <= 0: continue
                        city = city.zfill(5)
                        name = (row.get(fields["NM_MUNICIPIO"]) or "").strip()
                        candidate = (row.get(fields["NM_VOTAVEL"]) or "").strip()
                        party_field = fields.get("SG_PARTIDO")
                        party = (row.get(party_field) or "").strip() if party_field else ""
                        state_turns[office].add(turn); seen_offices.add(office)
                        city_data = cities.setdefault(city,{"id":city,"name":name,"uf":state,"offices":{}})
                        if not city_data["name"] and name: city_data["name"] = name
                        detail = city_data["offices"].setdefault(office,{"turns":set(),"sections":{},"records":0})
                        detail["turns"].add(turn); detail["sections"].setdefault(turn,set()).add((zone,section))
                        key=(city,office)
                        stream=streams.pop(key,None)
                        if stream is None:
                            if len(streams)>=128:
                                old_key,old_stream=streams.popitem(last=False); old_stream.close(); raw_handles.pop(old_key).close()
                            folder=build_dir/"municipalities"/city
                            folder.mkdir(parents=True,exist_ok=True)
                            path=folder/f"{office}.jsonl.gz"
                            raw=path.open("ab" if path.exists() else "wb"); raw_handles[key]=raw
                            stream=io.TextIOWrapper(gzip.GzipFile(fileobj=raw,mode="wb",compresslevel=9,mtime=0),encoding="utf-8",newline="")
                        streams[key]=stream
                        local_field=fields.get("NR_LOCAL_VOTACAO")
                        local_code=(row.get(local_field) or "").strip() if local_field else ""
                        # [turn, zone, section, polling-place code, vote code, label, party, votes]
                        stream.write(json.dumps([turn,zone,section,local_code,vote_code,candidate,party,votes],ensure_ascii=False,separators=(",",":"))+"\n")
                        detail["records"]+=1; state_rows[office]+=1
            for stream in streams.values(): stream.close()
            for raw in raw_handles.values(): raw.close()
        missing={"PREFEITO","VEREADOR"}-seen_offices
        if missing: raise RuntimeError(f"{state}: cargos esperados ausentes: {sorted(missing)}")
        if not cities: raise RuntimeError(f"{state}: nenhum município com resultados")
        offices={code:{"name":OFFICE_NAMES[code],"turns":sorted(state_turns[code]),"data_status":"complete"} for code in sorted(seen_offices)}
        municipality_list=[]
        for code,city in cities.items():
            normalized={"id":code,"name":city["name"],"uf":state,"offices":{}}
            for office,detail in city["offices"].items():
                file=f"municipalities/{code}/{office}.jsonl.gz"
                normalized["offices"][office]={"file":file,"turns":sorted(detail["turns"]),"sections_by_turn":{t:len(x) for t,x in sorted(detail["sections"].items())},"records":detail["records"],"file_size_bytes":(build_dir/file).stat().st_size}
            municipality_list.append(normalized)
        index={"dataset":"Eleições municipais 2024 — votação por seção","uf":state,"source":source_url,"source_portal":PORTAL_URL,"municipality_count":len(cities),"offices":offices,"municipalities":sorted(municipality_list,key=lambda x:x["name"])}
        (build_dir/"index.json").write_text(json.dumps(index,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        manifest={"dataset":index["dataset"],"scope":{"country":"Brasil","state":state,"municipalities":len(cities)},"source":source_url,"source_portal":PORTAL_URL,"license":"Creative Commons Attribution (CC BY)","retrieved_at_utc":datetime.now(timezone.utc).isoformat(),"source_archive_size_bytes":archive_size,"source_archive_sha256":digest.hexdigest(),"source_archive_members":[m.filename for m in members],"office_turns":{code:sorted(values) for code,values in sorted(state_turns.items())},"office_rows":dict(sorted(state_rows.items())),"municipality_count":len(cities),"partition_count":sum(len(c["offices"]) for c in cities.values())}
        (build_dir/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        out_dir=Path("data/2024")/state
        if out_dir.exists(): shutil.rmtree(out_dir)
        build_dir.replace(out_dir)
        print(f"{state}: {len(cities)} municípios, {sum(state_rows.values()):,} registros; turnos {manifest['office_turns']}.")
    finally:
        for stream in streams.values():
            if not stream.closed: stream.close()
        for raw in raw_handles.values():
            if not raw.closed: raw.close()
        shutil.rmtree(temp_dir,ignore_errors=True)

if __name__=="__main__": main()
