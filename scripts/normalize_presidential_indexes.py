"""Reconcile presidential index summaries; preserve original partition records."""
import argparse, json, pathlib, urllib.request
SOURCES={t:f'https://resultados.tse.jus.br/oficial/ele2026/{e}/dados/br/br-c0001-e{e.zfill(6)}-u.json' for t,e in [('1','6257'),('2','6258')]}
INVALID={'95','96','97','98','99'}
def load_rosters():
    rosters={}
    for turn,url in SOURCES.items():
        data=json.load(urllib.request.urlopen(url,timeout=45))
        assert data['tf']=='s' and data['f']=='o' and data['t']==turn
        rosters[turn]={c['n'] for a in data['carg'][0]['agr'] for p in a['par'] for c in p['cand']}
    return rosters

def normalize_index(index,rosters):
    allowed=set.union(*rosters.values())|INVALID
    index['candidates']={code:meta for code,meta in index['candidates'].items() if code in allowed}
    for city in index['municipalities']:
        for turn,values in city['turns'].items():
            votes=values['votes'];before=sum(votes.values());technical=0
            for code in list(votes):
                if code not in INVALID and code not in rosters[turn]: technical+=votes.pop(code)
            if technical:votes['96']=votes.get('96',0)+technical
            values['technical_nulls']=values.get('technical_nulls',0)+technical
            values['valid']=sum(n for code,n in votes.items() if code not in INVALID)
            assert sum(votes.values())==before
    index['summary_classification']='Final national EA20 roster; technical options included in nulls; raw partition records preserved'
    index['summary_sources']=SOURCES
    return index

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='data/2026/presidencia');parser.add_argument('--snapshots');args=parser.parse_args()
    if args.snapshots:
        rosters={}
        for turn in ['1','2']:
            data=json.loads((pathlib.Path(args.snapshots)/('1-'+turn+'.json')).read_text(encoding='utf-8'))['data']
            rosters[turn]={c['n'] for a in data['carg'][0]['agr'] for p in a['par'] for c in p['cand']}
    else:rosters=load_rosters()
    count=0
    for path in pathlib.Path(args.root).glob('*/index.json'):
        data=normalize_index(json.loads(path.read_text(encoding='utf-8')),rosters)
        path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
        count+=len(data['municipalities'])
    print('Reconciled presidential summaries for',count,'municipalities')
