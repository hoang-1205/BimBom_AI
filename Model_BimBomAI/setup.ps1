param([ValidateSet('cpu','cuda')][string]$Backend = 'cuda')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & py -3.13 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Can Python 3.13 64-bit va Python Launcher.' }
}
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $pythonPath -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 13) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Moi truong Python 3.13 khong chay duoc.' }
$indexUrl = if ($Backend -eq 'cuda') { 'https://download.pytorch.org/whl/cu128' } else { 'https://download.pytorch.org/whl/cpu' }
$torchVersion = if ($Backend -eq 'cuda') { 'torch==2.9.1+cu128' } else { 'torch==2.9.1+cpu' }
& $pythonPath -m pip install $torchVersion --index-url $indexUrl
if ($LASTEXITCODE -ne 0) { throw 'Cai PyTorch that bai.' }
& $pythonPath -m pip install tokenizers==0.22.1
if ($LASTEXITCODE -ne 0) { throw 'Cai tokenizer that bai.' }
& $pythonPath -m pip freeze | Set-Content -LiteralPath '.\requirements.lock.txt' -Encoding utf8
& $pythonPath '.\kiem_tra.py'
if ($LASTEXITCODE -ne 0) { throw 'Kiem tra moi truong that bai.' }

