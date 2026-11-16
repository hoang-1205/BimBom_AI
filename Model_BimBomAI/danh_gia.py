import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
"""So sánh checkpoint trên validation được lưu trong từng checkpoint."""
import argparse
import json
import math
import time
from datetime import datetime
from pathlib import Path
import torch
import torch.nn.functional as F
import Chinh_Che_Do as C
from Model_BimBomAI.pipeline import ROOT, load_model, generate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('checkpoints', nargs='+', type=Path)
    p.add_argument('--device', choices=['cpu', 'cuda', 'auto'])
    a = p.parse_args()
    device = C.lay_thiet_bi(a.device)
    torch.set_num_threads(4)
    rows = []
    for path in a.checkpoints:
        model, tokenizer, saved = load_model(path, device)
        model.eval()
        if device.type == 'cuda':
            torch.cuda.reset_peak_memory_stats()
        source = torch.tensor(saved['data']['validation'], dtype=torch.long)
        length = min(model.context, len(source)-1)
        gen = torch.Generator().manual_seed(123)
        losses = []
        with torch.no_grad():
            for _ in range(10):
                i = torch.randint(len(source)-length, (1,), generator=gen).item()
                x = source[i:i+length].unsqueeze(0).to(device)
                y = source[i+1:i+length+1].unsqueeze(0).to(device)
                losses.append(F.cross_entropy(model(x).flatten(0,1), y.flatten()).item())
        if device.type == 'cuda':
            torch.cuda.synchronize()
        start = time.perf_counter()
        torch.manual_seed(123)
        sample = generate(model, tokenizer, 'BimBom', 40, .8, device)
        if device.type == 'cuda':
            torch.cuda.synchronize()
        loss = sum(losses)/len(losses)
        rows.append(dict(checkpoint=str(path.resolve()), step=saved['step'],
            dataset=saved['manifest']['dataset_sha256'], validation_loss=loss,
            perplexity=math.exp(min(loss,80)), sample=sample, generation_seconds=time.perf_counter()-start,
            peak_vram_bytes=torch.cuda.max_memory_allocated() if device.type == 'cuda' else 0))
        del model
    out = ROOT / 'Ket_Qua/Danh_Gia_BimBom' / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)
    print('Chỉ so sánh loss trực tiếp khi dataset/tokenizer giống nhau.')
if __name__ == '__main__':
    main()

