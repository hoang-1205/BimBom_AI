"""Move only verified inputs of a completed training run into Da_Hoc."""
import hashlib
from pathlib import Path
from .document_reader import extract_document
from .memory import read_approved
from .runtime import atomic_json


def checked_path(path, boundary):
    """Resolve and reject links/junctions before any file move."""
    boundary = Path(boundary).absolute()
    path = Path(path).absolute()
    if not path.is_relative_to(boundary) or not path.resolve().is_relative_to(boundary.resolve()):
        raise ValueError('Đường dẫn nằm ngoài thư mục được phép.')
    for part in (path, *path.parents):
        if part.is_symlink() or part.is_junction():
            raise ValueError('Không tự chuyển file qua liên kết/junction.')
        if part == boundary:
            break
    return path.resolve()


def file_hash(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def snapshot_sources(manifest, stage, root):
    """Prove that current source content still matches the data in the checkpoint."""
    learning = checked_path(Path(root) / 'Hoc_BimBom', root)
    sources = manifest.get('source_documents')
    if sources is None:
        sources = manifest.get('train', []) + manifest.get('validation', [])
    report = dict(files=[], skipped=[])
    seen = set()
    for entry in sources:
        source = entry.get('source', '')
        if source in seen:
            continue
        seen.add(source)
        try:
            path = checked_path(source, learning)
            before = file_hash(path)
            if stage == 'sft':
                digest = read_approved(path)['reviewed_sha256']
            else:
                digest = hashlib.sha256(extract_document(path)['text'].encode()).hexdigest()
            if digest != entry.get('source_sha256', entry.get('sha256')) or file_hash(path) != before:
                raise ValueError('File đã thay đổi so với dữ liệu dùng để học; giữ nguyên tại chỗ.')
            item = dict(source=str(path), relative=str(path.relative_to(learning)), sha256=before)
            for name in ('split_manifest', 'split_part', 'original_source'):
                if name in entry:
                    item[name] = entry[name]
            report['files'].append(item)
        except (OSError, ValueError) as error:
            report['skipped'].append(dict(source=source, reason=str(error)))
    return report


def archive_completed_inputs(snapshot, root, run, reason, initial_step, final_step,
                             checkpoint, enabled=True):
    """Journal each move after the final checkpoint has been saved and validated."""
    if not enabled or final_step <= initial_step or reason not in ('target_reached', 'early_stopping'):
        return None
    from .checkpoint import validate, optimizer_steps
    state = validate(checkpoint)
    if optimizer_steps(state) != final_step:
        raise ValueError('Checkpoint cuối không khớp bước đã hoàn thành; chưa chuyển tài liệu.')
    root = Path(root).resolve()
    run = checked_path(run, root / 'Ket_Qua/Checkpoint_BimBom')
    destination = checked_path(root / 'Da_Hoc' / run.name, root)
    destination.mkdir(parents=True, exist_ok=False)
    report = dict(reason=reason, initial_step=initial_step, final_step=final_step,
                  checkpoint=str(checkpoint), moved=[], skipped=list(snapshot['skipped']), pending=None)
    journal = run / 'archived_sources.json'
    atomic_json(journal, report)
    for entry in snapshot['files']:
        try:
            source = checked_path(entry['source'], root / 'Hoc_BimBom')
            target = checked_path(destination / entry['relative'], destination)
            if file_hash(source) != entry['sha256']:
                raise ValueError('File đã sửa trong lúc học; không chuyển bản mới.')
            target.parent.mkdir(parents=True, exist_ok=True)
            # Recheck resolved targets after directory creation; never overwrite a file.
            checked_path(target, root)
            if target.exists():
                raise FileExistsError('Đích đã tồn tại; không ghi đè.')
            report['pending'] = dict(source=str(source), destination=str(target), sha256=entry['sha256'])
            atomic_json(journal, report)
            from .auto_split import record_archive_intent
            record_archive_intent(entry, target, root)
            # Same-volume rename on Windows fails if destination already exists.
            source.rename(target)
            report['moved'].append(report['pending'])
        except (OSError, ValueError) as error:
            report['skipped'].append(dict(source=entry['source'], reason=str(error)))
        report['pending'] = None
        atomic_json(journal, report)
    print(f'Da_Hoc: đã chuyển {len(report["moved"])} file; giữ lại/bỏ qua {len(report["skipped"])} file. '
          f'Chi tiết: {journal}', flush=True)
    return report
