import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""Tra cứu từ khóa cục bộ, có nguồn; không cập nhật trọng số."""
import argparse
import hashlib
import json
import re
import unicodedata
from Model_BimBomAI.pipeline import ROOT, documents
from Model_BimBomAI.Ma_Nguon.runtime import atomic_json


def words(text):
    return set(re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold()))


def retrieve(query, folder=ROOT / 'Hoc_BimBom'):
    docs = documents(folder)
    fingerprint = hashlib.sha256(json.dumps([(d['source'], d['sha256']) for d in docs]).encode()).hexdigest()
    path = ROOT / 'Ket_Qua/Bo_Nho_BimBom' / 'index.json'
    try:
        old = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = {}
    valid_cache = (isinstance(old, dict) and old.get('fingerprint') == fingerprint
                   and isinstance(old.get('chunks'), list)
                   and all(isinstance(d, dict) and isinstance(d.get('source'), str)
                           and isinstance(d.get('text'), str) and type(d.get('chunk')) is int
                           and d['chunk'] > 0 for d in old['chunks']))
    if not valid_cache:
        chunks = [dict(source=d['source'], chunk=i//600+1, text=d['text'][i:i+800])
                  for d in docs for i in range(0, len(d['text']), 600)]
        old = dict(fingerprint=fingerprint, chunks=chunks, method='lexical-v1')
        atomic_json(path, old)
    terms = words(query)
    ranked = [(len(terms & words(d['text'])) / max(1, len(terms)), d) for d in old['chunks']]
    return [dict(score=s, **d) for s, d in sorted(ranked, key=lambda x: x[0], reverse=True)[:3] if s > 0]


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--query', required=True)
    a = p.parse_args()
    print(json.dumps(retrieve(a.query), ensure_ascii=False, indent=2))



