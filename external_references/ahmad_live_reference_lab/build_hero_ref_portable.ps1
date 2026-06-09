param(
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$OutputDir = "",
    [switch]$InstallPyInstaller,
    [switch]$SkipExeBuild,
    [switch]$PublicSafe,
    [switch]$NoClean,
    [switch]$Zip
)

$ErrorActionPreference = "Stop"

$LabRoot = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $LabRoot "..\..")
$TemplateRoot = Join-Path $RepoRoot "apps\hero_ref"
$DefaultOutput = Join-Path $LabRoot "dist\BidKingHeroRefPortable"
if (-not $OutputDir) {
    $OutputDir = $DefaultOutput
} elseif (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $LabRoot $OutputDir
}
$OutputFull = [System.IO.Path]::GetFullPath($OutputDir)
$LabFull = [System.IO.Path]::GetFullPath($LabRoot)
$DistFull = [System.IO.Path]::GetFullPath((Join-Path $LabRoot "dist"))

function Assert-PathUnder {
    param(
        [string]$Path,
        [string]$Root,
        [string]$Label
    )
    $ResolvedPath = [System.IO.Path]::GetFullPath($Path)
    $ResolvedRoot = [System.IO.Path]::GetFullPath($Root)
    if (-not $ResolvedPath.StartsWith($ResolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must stay under $ResolvedRoot, got $ResolvedPath"
    }
}

function Copy-Tree {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "Source not found: $Source"
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $null = & robocopy $Source $Destination /E /NFL /NDL /NJH /NJS /NP /XD __pycache__ .pytest_cache .mypy_cache .ruff_cache /XF *.pyc
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed: $Source -> $Destination (exit $LASTEXITCODE)"
    }
}

function Copy-FileChecked {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        throw "File not found: $Source"
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

if (-not (Test-Path -LiteralPath $TemplateRoot)) {
    throw "Portable app template not found: $TemplateRoot"
}

if (-not $SkipExeBuild) {
    $BuildArgs = @{
        PythonPath = $PythonPath
    }
    if ($InstallPyInstaller) {
        $BuildArgs["InstallPyInstaller"] = $true
    }
    if ($NoClean) {
        $BuildArgs["NoClean"] = $true
    }
    & (Join-Path $LabRoot "build_ahmad_ref_ui_exe.ps1") @BuildArgs
    if ($LASTEXITCODE) {
        exit $LASTEXITCODE
    }
    & (Join-Path $LabRoot "build_windivert_monitor_exe.ps1") @BuildArgs
    if ($LASTEXITCODE) {
        exit $LASTEXITCODE
    }
}

$UiDist = Join-Path $LabRoot "dist\BidKingHeroRef"
$UiExe = Join-Path $UiDist "BidKingHeroRef.exe"
if (-not (Test-Path -LiteralPath $UiExe)) {
    throw "Hero Ref UI exe not found. Build first or run without -SkipExeBuild: $UiExe"
}
$MonitorDist = Join-Path $LabRoot "dist\BidKingHeroMonitor"
$MonitorExe = Join-Path $MonitorDist "BidKingHeroMonitor.exe"
if (-not (Test-Path -LiteralPath $MonitorExe)) {
    throw "Hero Ref monitor exe not found. Build first or run without -SkipExeBuild: $MonitorExe"
}

Assert-PathUnder -Path $OutputFull -Root $DistFull -Label "OutputDir"
if (Test-Path -LiteralPath $OutputFull) {
    Remove-Item -LiteralPath $OutputFull -Recurse -Force
}
New-Item -ItemType Directory -Path $OutputFull -Force | Out-Null

Copy-Tree -Source $TemplateRoot -Destination $OutputFull
Copy-Tree -Source $UiDist -Destination (Join-Path $OutputFull "BidKingHeroRef")
Copy-Tree -Source $MonitorDist -Destination (Join-Path $OutputFull "BidKingHeroMonitor")
Copy-Tree -Source (Join-Path $RepoRoot "src") -Destination (Join-Path $OutputFull "src")

$ScriptsOut = Join-Path $OutputFull "scripts"
New-Item -ItemType Directory -Path $ScriptsOut -Force | Out-Null
$ScriptFiles = @(
    "resolve_python.ps1",
    "start_live_windivert_overlay.ps1",
    "run_windivert_live_monitor.py",
    "run_fatbeans_webhook_monitor.py",
    "diagnose_windivert.py",
    "live_status.ps1"
)
foreach ($Name in $ScriptFiles) {
    Copy-FileChecked -Source (Join-Path $RepoRoot "scripts\$Name") -Destination (Join-Path $ScriptsOut $Name)
}

Copy-FileChecked -Source (Join-Path $RepoRoot "pyproject.toml") -Destination (Join-Path $OutputFull "pyproject.toml")

$ProcessedOut = Join-Path $OutputFull "data\processed"
New-Item -ItemType Directory -Path $ProcessedOut -Force | Out-Null
Get-ChildItem -Path (Join-Path $RepoRoot "data\processed") -File -Filter "*.json" |
    ForEach-Object {
        Copy-FileChecked -Source $_.FullName -Destination (Join-Path $ProcessedOut $_.Name)
    }

$RawTablesOut = Join-Path $OutputFull "data\raw\tables"
New-Item -ItemType Directory -Path $RawTablesOut -Force | Out-Null
if ($PublicSafe) {
    @"
This public-safe package does not include raw game tables.

Before running Hero Ref, use the package root script:

  导入本机游戏表.bat

Choose one of these local folders:

- BidKing game root, e.g. ...\steamapps\common\BidKing
- BidKing_Data\StreamingAssets
- BidKing_Data\StreamingAssets\Tables

The importer will copy at least:

- BidMap.txt
- Drop.txt
- Item.txt

Do not publish raw game table files unless you have permission.
"@ | Set-Content -Path (Join-Path $RawTablesOut "PUT_TABLES_HERE.txt") -Encoding utf8
} else {
    $RawTablesSource = Join-Path $RepoRoot "data\raw\tables"
    if (-not (Test-Path -LiteralPath $RawTablesSource)) {
        throw "Raw tables not found: $RawTablesSource"
    }
    Copy-Tree -Source $RawTablesSource -Destination $RawTablesOut
}

New-Item -ItemType Directory -Path (Join-Path $OutputFull "data\logs\live") -Force | Out-Null

$ConfigPath = Join-Path $OutputFull "src\bidking_lab\config.py"
if (Test-Path -LiteralPath $ConfigPath) {
    $ConfigText = Get-Content -LiteralPath $ConfigPath -Raw
    $ConfigText = $ConfigText -replace '\s*r"C:\\xiangmuyunxing\\steamapps\\common\\BidKing",\r?\n', ''
    Set-Content -Path $ConfigPath -Value $ConfigText -Encoding utf8
}

$Commit = ""
try {
    $Commit = (& git -C $RepoRoot rev-parse --short HEAD 2>$null).Trim()
} catch {
}

$ManifestPath = Join-Path $OutputFull "BUILD_MANIFEST.txt"
@"
BidKing Hero Ref portable package
BuiltAt: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
SourceCommit: $Commit
PublicSafe: $([bool]$PublicSafe)
IncludesRawTables: $(-not [bool]$PublicSafe)
UI: BidKingHeroRef\BidKingHeroRef.exe
Monitor: BidKingHeroMonitor\BidKingHeroMonitor.exe
Launcher: Start-HeroRef.bat / Start-HeroRef.ps1
RequiresExternalPython: False

Before public release, review README.zh-CN.md and TRUST_AND_SECURITY.zh-CN.md.
"@ | Set-Content -Path $ManifestPath -Encoding utf8

$SensitivePatterns = @(
    "C:\\Users\\shenc",
    "C:\\xiangmuyunxing\\biancheng",
    ".codex",
    "data\\logs\\live\\raw",
    "data\\samples\\fatbeans"
)
$TextFiles = Get-ChildItem -Path $OutputFull -Recurse -File |
    Where-Object {
        $_.Extension -in @(".ps1", ".bat", ".md", ".txt", ".py", ".toml")
    }
$Findings = @()
foreach ($File in $TextFiles) {
    $Text = Get-Content -LiteralPath $File.FullName -Raw -ErrorAction SilentlyContinue
    foreach ($Pattern in $SensitivePatterns) {
        if ($Text -like "*$Pattern*") {
            $Findings += "$($File.FullName): $Pattern"
        }
    }
}
if ($Findings.Count -gt 0) {
    Write-Host "Potential package path/sensitive findings:" -ForegroundColor Yellow
    $Findings | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
    throw "Package sensitive/path scan failed."
}

Write-Host ""
Write-Host "Built Hero Ref portable package:" -ForegroundColor Green
Write-Host "  $OutputFull"
Write-Host ""
Write-Host "Start with:" -ForegroundColor Cyan
Write-Host "  $OutputFull\Start-HeroRef.bat"
Write-Host ""
if ($PublicSafe) {
    Write-Host "PublicSafe mode: raw tables are excluded; users can run 导入本机游戏表.bat after unzip." -ForegroundColor Yellow
} else {
    Write-Host "Local package includes data\raw\tables. Do not publish those files without permission." -ForegroundColor Yellow
}

if ($Zip) {
    $ZipPath = "$OutputFull.zip"
    Assert-PathUnder -Path $ZipPath -Root $DistFull -Label "Zip output"
    if (Test-Path -LiteralPath $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }
    Compress-Archive -Path (Join-Path $OutputFull "*") -DestinationPath $ZipPath -Force
    Write-Host ""
    Write-Host "Built zip:" -ForegroundColor Green
    Write-Host "  $ZipPath"
}
