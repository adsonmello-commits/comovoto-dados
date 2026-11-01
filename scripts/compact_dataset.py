"""Canonicalize published partitions without changing any electoral record."""
import argparse, concurrent.futures, gzip, hashlib, json, pathlib

REVISION = 2

def decode_records(text):
    decoder = json.JSONDecoder()
    position = 0
    while position < len(text):
        if text[position].isspace(): position += 1; continue
        if text.startswith('\\n', position): position += 2; continue
        row, position = decoder.raw_decode(text, position)
        yield row

def compact_file(path, expected):
    before = path.read_bytes()
    rows = list(decode_records(gzip.decompress(before).decode('utf-8')))
    if len(rows) != expected: raise ValueError(f'{path}: {len(rows)} != {expected}')
    canonical = ''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows).encode('utf-8')
    after = gzip.compress(canonical, compresslevel=9, mtime=0)
    # Independent decoder verifies integrity and exact records before replacement.
    if [json.loads(line) for line in gzip.decompress(after).splitlines()] != rows:
        raise ValueError(f'{path}: round-trip mismatch')
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(after)
    temporary.replace(path)
    return {'file_size_bytes': len(after), 'sha256': hashlib.sha256(after).hexdigest(), 'before': len(before), 'after': len(after)}

def compact_state(folder):
    index_path = folder / 'index.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    manifest_path = folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('format_revision') == REVISION: return {'before': 0, 'after': 0, 'files': 0}
    tasks = [(folder / meta['file'], meta) for city in index['municipalities'] for meta in city['offices'].values()]
    before = after = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = pool.map(lambda task: compact_file(task[0], task[1]['records']), tasks)
        for (_, meta), result in zip(tasks, results):
            before += result.pop('before'); after += result.pop('after'); meta.update(result)
    index['format_revision'] = REVISION
    manifest.update(format_revision=REVISION, partition_format='jsonl-utf8-single-gzip',
                    partition_bytes_before=before, partition_bytes_after=after)
    index_path.write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return {'before': before, 'after': after, 'files': len(tasks)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root', default='data'); args = parser.parse_args()
    total = {'before': 0, 'after': 0, 'files': 0}
    for year in ['2024', '2026']:
        for folder in sorted((pathlib.Path(args.root) / year).glob('*')):
            if not (folder / 'index.json').is_file() or folder.name == 'presidencia': continue
            result = compact_state(folder)
            for key in total: total[key] += result[key]
            print(year, folder.name, result, flush=True)
    print('TOTAL', total, flush=True)

