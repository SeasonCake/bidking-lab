param(
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$Version = "0.1.4",
    [string]$OutputDir = "",
    [switch]$InstallPyInstaller,
    [switch]$SkipExeBuild,
    [switch]$PublicSafe,
    [ValidateSet("engineering", "portable", "public-safe")]
    [string]$DiagnosticProfile = "",
    [switch]$NoClean,
    [switch]$Zip
)

$ErrorActionPreference = "Stop"

$LabRoot = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $LabRoot "..\..")
$TemplateRoot = Join-Path $RepoRoot "apps\hero_ref"
if ($Version -notmatch '^[0-9A-Za-z][0-9A-Za-z._-]*$') {
    throw "Version must be a simple label such as 0.1.4; do not include dates, paths, or dirty markers."
}
if ($Version -match '(?i)dirty' -or $Version -match '\d{8}') {
    throw "Version must not include dirty markers or date chunks; use a plain version such as 0.1.4."
}
$PackageKind = if ($PublicSafe) { "public-safe" } else { "full" }
$DefaultOutput = Join-Path $LabRoot "dist\BidKingHeroRef-v$Version-$PackageKind"
if (-not $OutputDir) {
    $OutputDir = $DefaultOutput
} elseif (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path $LabRoot $OutputDir
}
$OutputFull = [System.IO.Path]::GetFullPath($OutputDir)
$OutputLeaf = Split-Path -Leaf $OutputFull
if ($OutputLeaf -match '(?i)dirty' -or $OutputLeaf -match '\d{8}') {
    throw "OutputDir package name must not include dirty markers or date chunks; use BidKingHeroRef-v$Version-$PackageKind."
}
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

function Write-Utf8BomFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $Text = Get-Content -LiteralPath $Path -Raw
    [System.IO.File]::WriteAllText($Path, $Text, [System.Text.UTF8Encoding]::new($true))
}

function Write-Utf8NoBomCrLfFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }
    $Text = [System.IO.File]::ReadAllText($Path, [System.Text.UTF8Encoding]::new($false, $true))
    $Text = $Text -replace "`r?`n", "`r`n"
    [System.IO.File]::WriteAllText($Path, $Text, [System.Text.UTF8Encoding]::new($false))
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
$ChineseBatchLaunchers = @(
    "管理员启动HeroRef_悬浮窗.bat",
    "管理员启动HeroRef_任务栏窗口.bat",
    "导入本机游戏表.bat",
    "停止HeroRef.bat"
)
foreach ($Name in $ChineseBatchLaunchers) {
    $ChineseBatchPath = Join-Path $OutputFull $Name
    if (Test-Path -LiteralPath $ChineseBatchPath) {
        Remove-Item -LiteralPath $ChineseBatchPath -Force
    }
}
$TaskbarHelperOut = Join-Path $OutputFull "Start-HeroRef-Taskbar.ps1"
if (Test-Path -LiteralPath $TaskbarHelperOut) {
    Remove-Item -LiteralPath $TaskbarHelperOut -Force
}
$TaskbarBatchOut = Join-Path $OutputFull "Start-HeroRef-Taskbar.bat"
if (Test-Path -LiteralPath $TaskbarBatchOut) {
@"
@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-HeroRef.ps1" -ShowTaskbar %*
"@ | Set-Content -Path $TaskbarBatchOut -Encoding utf8
}
Get-ChildItem -Path $OutputFull -Recurse -File -Filter "*.bat" |
    ForEach-Object {
        Write-Utf8NoBomCrLfFile -Path $_.FullName
    }
$DefaultDiagnosticProfile = if ($DiagnosticProfile) {
    $DiagnosticProfile
} elseif ($PublicSafe) {
    "public-safe"
} else {
    "portable"
}
if ($PublicSafe -and $DefaultDiagnosticProfile -ne "public-safe") {
    Write-Host "Warning: -PublicSafe is usually paired with -DiagnosticProfile public-safe; current profile is $DefaultDiagnosticProfile." -ForegroundColor Yellow
}
$StartHeroOut = Join-Path $OutputFull "Start-HeroRef.ps1"
if (Test-Path -LiteralPath $StartHeroOut) {
    $StartHeroText = Get-Content -LiteralPath $StartHeroOut -Raw
    $StartHeroText = $StartHeroText -replace '\[string\]\$DiagnosticProfile = "[^"]+"', "[string]`$DiagnosticProfile = `"$DefaultDiagnosticProfile`""
    Set-Content -Path $StartHeroOut -Value $StartHeroText -Encoding utf8
}
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

$ResolvePythonOut = Join-Path $ScriptsOut "resolve_python.ps1"
if (Test-Path -LiteralPath $ResolvePythonOut) {
    $ResolveText = Get-Content -LiteralPath $ResolvePythonOut -Raw
    $ResolveText = $ResolveText -replace '# Default: C:\\Python313\\python\.exe \(override with -PythonPath or \$env:BIDKING_PYTHON\)\.', '# Default: no bundled Python fallback; override with -PythonPath or $env:BIDKING_PYTHON.'
    $ResolveText = $ResolveText -replace '\$script:BidKingDefaultPython313 = "C:\\Python313\\python\.exe"', '$script:BidKingDefaultPython313 = ""'
    Set-Content -Path $ResolvePythonOut -Value $ResolveText -Encoding utf8
}

$MonitorStartOut = Join-Path $ScriptsOut "start_live_windivert_overlay.ps1"
if (Test-Path -LiteralPath $MonitorStartOut) {
    $MonitorStartText = Get-Content -LiteralPath $MonitorStartOut -Raw
    $MonitorStartText = $MonitorStartText -replace '\[string\]\$PythonPath = "C:\\Python313\\python\.exe"', '[string]$PythonPath = ""'
    $MonitorStartText = $MonitorStartText -replace 'Pass -PythonPath C:\\Python313\\python\.exe', 'Pass -PythonPath <path-to-python.exe>'
    Set-Content -Path $MonitorStartOut -Value $MonitorStartText -Encoding utf8
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

  Import-LocalTables.bat

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

Get-ChildItem -Path $OutputFull -Recurse -File -Filter "*.ps1" |
    ForEach-Object {
        Write-Utf8BomFile -Path $_.FullName
    }

$Commit = ""
$DirtyWorktree = "unknown"
try {
    $Commit = (& git -C $RepoRoot rev-parse --short HEAD 2>$null).Trim()
    $DirtyStatus = (& git -C $RepoRoot status --porcelain 2>$null)
    $DirtyWorktree = if ($DirtyStatus) { "true" } else { "false" }
} catch {
}

$ManifestPath = Join-Path $OutputFull "BUILD_MANIFEST.txt"
@"
BidKing Hero Ref portable package
BuiltAt: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
SourceCommit: $Commit
DirtyWorktree: $DirtyWorktree
PackageVersion: v$Version
PackageKind: $PackageKind
PublicSafe: $([bool]$PublicSafe)
IncludesRawTables: $(-not [bool]$PublicSafe)
PackageProfile: $DefaultDiagnosticProfile
UI: BidKingHeroRef\BidKingHeroRef.exe
Monitor: BidKingHeroMonitor\BidKingHeroMonitor.exe
LauncherFloating: Start-HeroRef.bat
LauncherTaskbar: Start-HeroRef-Taskbar.bat
LauncherImportTables: Import-LocalTables.bat
LauncherStop: Stop-HeroRef.bat
LauncherPowerShell: Start-HeroRef.ps1
RequiresExternalPython: False
DefaultDiagnosticProfile: $DefaultDiagnosticProfile
Docs: 使用说明.txt / 管理员运行说明.txt / 火绒拦截说明.txt / VPN或UU备用启动.txt

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
Write-Host "Built Hero Ref $PackageKind package:" -ForegroundColor Green
Write-Host "  $OutputFull"
Write-Host ""
Write-Host "Start with floating overlay:" -ForegroundColor Cyan
Write-Host "  $OutputFull\Start-HeroRef.bat"
Write-Host "Start with taskbar window:" -ForegroundColor Cyan
Write-Host "  $OutputFull\Start-HeroRef-Taskbar.bat"
Write-Host "Support tools:" -ForegroundColor Cyan
Write-Host "  $OutputFull\Import-LocalTables.bat"
Write-Host "  $OutputFull\Stop-HeroRef.bat"
Write-Host ""
if ($PublicSafe) {
    Write-Host "PublicSafe mode: raw tables are excluded; users can run Import-LocalTables.bat after unzip." -ForegroundColor Yellow
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
    $RepoDist = Join-Path $RepoRoot "dist"
    New-Item -ItemType Directory -Path $RepoDist -Force | Out-Null
    $RepoZipPath = Join-Path $RepoDist (Split-Path -Leaf $ZipPath)
    Copy-Item -LiteralPath $ZipPath -Destination $RepoZipPath -Force
    Write-Host ""
    Write-Host "Built zip:" -ForegroundColor Green
    Write-Host "  $ZipPath"
    Write-Host "Repo dist copy:" -ForegroundColor Green
    Write-Host "  $RepoZipPath"
}
