# BidKing Lab v1.0.0 — one-click Streamlit launcher (Windows PowerShell)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Python {
    foreach ($cmd in @("py -3.13", "py -3.12", "py -3.11", "py -3.10", "python")) {
        try {
            $ver = Invoke-Expression "$cmd -c `"import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')`"" 2>$null
            if ($LASTEXITCODE -ne 0) { continue }
            $parts = $ver.Trim().Split(".")
            if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10) {
                return $cmd
            }
        } catch {
            continue
        }
    }
    return $null
}

$pyCmd = Find-Python
if (-not $pyCmd) {
    Write-Host ""
    Write-Host "未找到 Python 3.10+。请先安装 Python 3.13 并勾选 Add to PATH：" -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host "使用 Python: $pyCmd" -ForegroundColor Cyan

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "首次运行：创建虚拟环境 .venv ..." -ForegroundColor Cyan
    Invoke-Expression "$pyCmd -m venv .venv"
}

Write-Host "安装 / 更新依赖（首次约 1–3 分钟）..." -ForegroundColor Cyan
& $venvPy -m pip install -q --upgrade pip
& $venvPy -m pip install -q -r requirements-release.txt

$tablesDir = Join-Path $PSScriptRoot "data\raw\tables"
$bidMap = Join-Path $tablesDir "BidMap.txt"
if (-not (Test-Path $bidMap)) {
    Write-Host ""
    Write-Host "缺少 data\raw\tables\BidMap.txt — 无法加载地图数据。" -ForegroundColor Red
    Write-Host "请确认下载的是 GitHub Release 附带的完整 zip（含 data 目录）。" -ForegroundColor Yellow
    Write-Host "若从 git clone 安装，请设置游戏路径后运行 scripts\copy_game_tables.ps1" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host ""
Write-Host "启动 BidKing Lab（Streamlit）..." -ForegroundColor Green
Write-Host "浏览器将打开 http://localhost:8501 ；关闭本窗口即停止服务。" -ForegroundColor Gray
Write-Host ""

& $venvPy -m streamlit run app/streamlit_app.py
