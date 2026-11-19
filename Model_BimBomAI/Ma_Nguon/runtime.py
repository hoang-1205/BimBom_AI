"""Shared paths, atomic writes and an OS-owned process lock."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import queue
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
DIRECTORIES = (
    'Da_Hoc', 'Hoc_BimBom/Da_Chia',
    'Hoc_BimBom/Tai_Lieu', 'Hoc_BimBom/Hoi_Thoai_Goc', 'Hoc_BimBom/Cho_Duyet',
    'Hoc_BimBom/Du_Lieu_Huan_Luyen/Pretrain', 'Hoc_BimBom/Du_Lieu_Huan_Luyen/Chat_SFT',
    'Bo_Nho_BimBom/Ngan_Han', 'Bo_Nho_BimBom/Dai_Han', 'Bo_Nho_BimBom/Chi_Muc',
    'Ky_Nang_BimBom_Hoc_Duoc/Quy_Tac_Tra_Loi', 'Ky_Nang_BimBom_Hoc_Duoc/Quy_Trinh',
    'Ky_Nang_BimBom_Hoc_Duoc/Vi_Du_Chuan', 'Ket_Qua/Checkpoint_BimBom',
    'Ket_Qua/Nhat_Ky_Chat', 'Ket_Qua/Nhat_Ky_Train', 'Ket_Qua/Danh_Gia',
)
_active_session = None


class StopRequested(KeyboardInterrupt):
    """Cooperative shutdown, never a kill of arbitrary Python processes."""


def _lock(handle, release=False):
    handle.seek(0)
    if os.name == 'nt':
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK if release else msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_UN if release else fcntl.LOCK_EX | fcntl.LOCK_NB)


def active_session(root=ROOT):
    path = root / 'Ket_Qua/.session.lock'
    if not path.exists():
        return None
    with path.open('r+b') as handle:
        try:
            _lock(handle)
        except OSError:
            metadata = root / 'Ket_Qua/.session.json'
            try:
                value = json.loads(metadata.read_text(encoding='utf-8'))
                if not isinstance(value, dict) or not isinstance(value.get('id'), str) or not value['id']:
                    raise ValueError('Metadata không hợp lệ')
                return value
            except (OSError, ValueError):
                return {'id': None, 'kind': 'starting'}
        else:
            _lock(handle, release=True)
            return None


def request_stop(root=ROOT):
    session = active_session(root)
    if session is None:
        return None
    if not session.get('id'):
        raise RuntimeError('Phiên đang khởi động hoặc dùng mã cũ; thử lại sau vài giây, hoặc Ctrl+C tại phiên đó.')
    atomic_json(root / 'Ket_Qua/.stop.json', {'id': session['id'], 'requested_at': now()})
    return session


def wait_stopped(identifier, timeout=30, root=ROOT):
    deadline = time.monotonic() + timeout
    while True:
        session = active_session(root)
        if session is None or session.get('id') != identifier:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(.1)


def stop_requested():
    if _active_session is None:
        return False
    root, identifier = _active_session
    try:
        value = json.loads((root / 'Ket_Qua/.stop.json').read_text(encoding='utf-8'))
        return isinstance(value, dict) and value.get('id') == identifier
    except (OSError, ValueError):
        return False


def check_stop():
    if stop_requested():
        raise StopRequested('Đã nhận yêu cầu tắt BimBom.')


def read_input(prompt):
    """Keep the main thread responsive while console input waits in a daemon."""
    check_stop()
    result = queue.Queue(maxsize=1)
    def read():
        try:
            result.put((True, input(prompt)))
        except BaseException as error:
            result.put((False, error))
    threading.Thread(target=read, daemon=True).start()
    while True:
        check_stop()
        try:
            ok, value = result.get(timeout=.1)
        except queue.Empty:
            continue
        check_stop()
        if ok:
            return value
        raise value


def initialize(root=ROOT):
    for name in DIRECTORIES:
        (root / name).mkdir(parents=True, exist_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         suffix='.tmp', delete=False) as f:
            name = Path(f.name)
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name is not None:
            name.unlink(missing_ok=True)


def append_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
        f.flush()


@contextmanager
def session_lock(root=ROOT, kind='work'):
    """Never delete the lock file: the OS releases its byte lock on process exit."""
    global _active_session
    path = root / 'Ket_Qua' / '.session.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as f:
        if path.stat().st_size == 0:
            f.write(b'0')
            f.flush()
        f.seek(0)
        try:
            _lock(f)
        except OSError as error:
            raise RuntimeError('BimBom đang chat/train/đánh giá ở phiên khác. Hãy đóng phiên đó trước.') from error
        identifier = uuid.uuid4().hex
        previous = _active_session
        metadata = root / 'Ket_Qua/.session.json'
        stop = root / 'Ket_Qua/.stop.json'
        try:
            stop.unlink(missing_ok=True)
            atomic_json(metadata, dict(id=identifier, pid=os.getpid(), kind=kind, started_at=now()))
            _active_session = (root, identifier)
            yield
        finally:
            _active_session = previous
            try:
                metadata.unlink(missing_ok=True)
                stop.unlink(missing_ok=True)
            finally:
                _lock(f, release=True)
