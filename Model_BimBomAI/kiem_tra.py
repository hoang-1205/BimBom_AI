import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json
import platform
import sys
import torch
import tokenizers
import Chinh_Che_Do as C
if sys.version_info[:2] != (3, 13):
    raise SystemExit('Dự án sử dụng Python 3.13.')
print(json.dumps(dict(python=platform.python_version(), executable=sys.executable,
    torch=str(torch.__version__), tokenizers=tokenizers.__version__, cuda_runtime=torch.version.cuda,
    cuda_available=torch.cuda.is_available(), device=str(C.lay_thiet_bi()),
    gpu=torch.cuda.get_device_name() if torch.cuda.is_available() else None), indent=2))

