"""Gom dữ liệu v2; có --train thì chạy pipeline huấn luyện mới."""
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import ROOT, prepare

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder', type=Path, default=ROOT / 'Hoc_BimBom')
    p.add_argument('--train', action='store_true')
    p.add_argument('--include-approved', action='store_true')
    p.add_argument('--steps', type=int, default=600)
    a = p.parse_args()
    if a.train:
        command = [sys.executable, str(ROOT / 'train.py'), '--folder', str(a.folder), '--steps', str(a.steps)]
        if a.include_approved:
            command.append('--include-approved')
        subprocess.run(command, check=True)
    else:
        out = ROOT / 'Ket_Qua/Du_Lieu_Da_Xu_Ly' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        prepare(a.folder, out, C.VOCAB_SIZE, C.SEED, a.include_approved)
        print(out)
if __name__ == '__main__':
    main()


