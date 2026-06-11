param(
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$Name = "BidKingHeroMonitor",
    [switch]$InstallPyInstaller,
    [switch]$OneFile,
    [switch]$NoClean
)

$ErrorActionPreference = "Stop"

$LabRoot = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $LabRoot "..\..")
$Entry = Join-Path $RepoRoot "scripts\run_windivert_live_monitor.py"
$DistPath = Join-Path $LabRoot "dist"
$BuildPath = Join-Path $LabRoot "build"

function Test-PyInstaller {
    & $PythonPath -m PyInstaller --version *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python not found: $PythonPath"
}
if (-not (Test-Path -LiteralPath $Entry)) {
    throw "Entry script not found: $Entry"
}
if (-not (Test-PyInstaller)) {
    if (-not $InstallPyInstaller) {
        throw "PyInstaller is not installed for $PythonPath. Re-run with -InstallPyInstaller, or run: `"$PythonPath`" -m pip install pyinstaller"
    }
    & $PythonPath -m pip install pyinstaller
    if ($LASTEXITCODE) {
        exit $LASTEXITCODE
    }
}

$Args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--console",
    "--name", $Name,
    "--distpath", $DistPath,
    "--workpath", $BuildPath,
    "--specpath", $BuildPath,
    "--paths", (Join-Path $RepoRoot "scripts"),
    "--paths", (Join-Path $RepoRoot "src"),
    "--hidden-import", "run_fatbeans_webhook_monitor",
    "--hidden-import", "pydivert",
    "--hidden-import", "pydivert.windivert",
    "--hidden-import", "pydivert.packet",
    "--hidden-import", "pydivert.consts",
    "--collect-data", "pydivert",
    "--collect-binaries", "pydivert"
)
if (-not $NoClean) {
    $Args += "--clean"
}
if ($OneFile) {
    $Args += "--onefile"
}
$Args += $Entry

Write-Host "== Build Hero Ref WinDivert monitor exe ==" -ForegroundColor Cyan
Write-Host "Python: $PythonPath"
Write-Host "Entry:  $Entry"
Write-Host "Dist:   $DistPath"
Write-Host ""

& $PythonPath @Args
if ($LASTEXITCODE) {
    exit $LASTEXITCODE
}

$ExePath = if ($OneFile) {
    Join-Path $DistPath "$Name.exe"
} else {
    Join-Path $DistPath "$Name\$Name.exe"
}

Write-Host ""
Write-Host "Built: $ExePath" -ForegroundColor Green
Write-Host "Monitor exe is still a WinDivert capture tool: users must run it elevated and may need to trust it in security software." -ForegroundColor Yellow
