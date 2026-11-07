# T0.3 — Đóng gói app hello thành 1 file .exe và chạy tự kiểm tra.
# Chạy từ gốc repo:  powershell -ExecutionPolicy Bypass -File spikes\t0-3-hello-exe\build.ps1
$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$py = Join-Path $here "..\..\.venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Chưa có .venv ở gốc repo. Tạo trước:"
    Write-Host "  py -3.14 -m venv .venv"
    Write-Host "  .venv\Scripts\python -m pip install -r requirements-dev.txt"
    exit 1
}

& $py -m PyInstaller --noconfirm --clean --onefile --windowed `
    --name HelloGiaSu `
    --distpath (Join-Path $here "dist") `
    --workpath (Join-Path $here "build") `
    --specpath $here `
    (Join-Path $here "hello.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$exe = Join-Path $here "dist\HelloGiaSu.exe"
$out = Join-Path $here "dist\selftest.json"
$size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "Đã tạo $exe ($size MB). Đang chạy tự kiểm tra..."

$p = Start-Process -FilePath $exe -ArgumentList "--selftest", "`"$out`"" -Wait -PassThru
Write-Host "Mã thoát: $($p.ExitCode) (0 = đạt)"
Get-Content $out -Encoding utf8
exit $p.ExitCode
