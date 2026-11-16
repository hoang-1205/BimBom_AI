"""Local reviewed knowledge store. No network and no automatic approval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import uuid
import sys

STORE = Path(__file__).resolve().parent.parent / 'Du_Lieu/Ky_Nang_BimBom_Hoc_Duoc'


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def digest(entry):
    body = {key: entry[key] for key in ('question', 'answer', 'workflow', 'source')}
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def initialize(store=STORE):
    for name in ('Ban_Nhap', 'Da_Duyet'):
        (store / name).mkdir(parents=True, exist_ok=True)


def save_draft(question, answer, workflow='', source='manual', store=STORE):
    if not question.strip() or not answer.strip():
        raise ValueError('Question and answer must not be empty.')
    initialize(store)
    identifier = uuid.uuid4().hex
    entry = dict(id=identifier, status='draft', question=question.strip(),
                 answer=answer.strip(), workflow=workflow.strip(), source=source,
                 created_at=datetime.now(timezone.utc).isoformat())
    path = store / 'Ban_Nhap' / f'{identifier}.json'
    with path.open('x', encoding='utf-8') as handle:
        json.dump(entry, handle, ensure_ascii=False, indent=2)
    return path


def approve(identifier, store=STORE):
    if not re.fullmatch(r'[0-9a-f]{32}', identifier):
        raise ValueError('Invalid ID; use the filename without .json.')
    path = store / 'Ban_Nhap' / f'{identifier}.json'
    entry = json.loads(path.read_text(encoding='utf-8-sig'))
    if entry['id'] != identifier or entry['status'] != 'draft':
        raise ValueError('Invalid draft metadata.')
    if not entry['question'].strip() or not entry['answer'].strip():
        raise ValueError('Empty question or answer.')
    entry.update(status='approved', approved_at=datetime.now(timezone.utc).isoformat())
    entry['reviewed_sha256'] = digest(entry)
    target = store / 'Da_Duyet' / path.name
    with target.open('x', encoding='utf-8') as handle:
        json.dump(entry, handle, ensure_ascii=False, indent=2)
    path.unlink()
    return target


def approved_entries(store=STORE):
    for path in sorted((store / 'Da_Duyet').glob('*.json')):
        try:
            entry = json.loads(path.read_text(encoding='utf-8-sig'))
            if (entry['status'] != 'approved' or entry['id'] != path.stem
                    or entry.get('reviewed_sha256') != digest(entry)
                    or not entry['question'].strip() or not entry['answer'].strip()):
                raise ValueError('Content changed or not reviewed')
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise ValueError(f'Invalid approved record {path}: {error}') from error
        yield path, entry


def training_documents(store=STORE):
    for path, entry in approved_entries(store):
        text = f"Câu hỏi: {entry['question']}\nCâu trả lời: {entry['answer']}"
        if entry['workflow']:
            text += f"\nQuy trình đã duyệt: {entry['workflow']}"
        yield str(path), text


def search(query, store=STORE):
    normalized = normalize(query)
    words = set(normalized.split())
    results = []
    for path, entry in approved_entries(store):
        question = normalize(entry['question'])
        exact = normalized == question
        candidates = set(question.split())
        score = len(words & candidates) / max(1, len(words | candidates))
        if exact or score > 0:
            results.append((exact, score, path, entry))
    return sorted(results, key=lambda item: (item[0], item[1]), reverse=True)[:5]


def main():
    if sys.version_info[:2] != (3, 13):
        raise SystemExit('BimBom AI requires Python 3.13 in Model_BimBomAI/.venv.')
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('luu')
    add.add_argument('--question', required=True)
    add.add_argument('--answer-file', type=Path, required=True)
    add.add_argument('--workflow-file', type=Path)
    review = commands.add_parser('duyet')
    review.add_argument('id')
    review.add_argument('--confirm', choices=['DA_KIEM_TRA'], required=True)
    find = commands.add_parser('tim')
    find.add_argument('--query', required=True)
    commands.add_parser('danhsach')
    args = parser.parse_args()
    initialize()
    try:
        if args.command == 'luu':
            answer = args.answer_file.read_text(encoding='utf-8-sig')
            workflow = args.workflow_file.read_text(encoding='utf-8-sig') if args.workflow_file else ''
            print(save_draft(args.question, answer, workflow, source=str(args.answer_file.resolve())))
        elif args.command == 'duyet':
            print(approve(args.id))
        elif args.command == 'danhsach':
            for folder in ('Ban_Nhap', 'Da_Duyet'):
                print(f'[{folder}]')
                for path in sorted((STORE / folder).glob('*.json')):
                    print(path.stem)
        else:
            results = search(args.query)
            if not results:
                print('Khong tim thay noi dung da duyet phu hop. Khong tu tao dap an.')
            for exact, score, path, entry in results:
                print('\n' + ('CAU HOI TRUNG KHOP' if exact else 'GOI Y GAN GIONG - CAN KIEM TRA'))
                print(f"ID: {entry['id']}\nNguon: {path}\nHoi: {entry['question']}\nDap: {entry['answer']}")
                if entry['workflow']:
                    print('Quy trinh: ' + entry['workflow'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()

