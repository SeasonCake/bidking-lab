param(
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$Name = "BidKingHeroRef",
    [switch]$InstallPyInstaller,
    [switch]$OneFile,
    [switch]$NoClean
)

$ErrorActionPreference = "Stop"

$LabRoot = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $LabRoot "..\..")
$Entry = Join-Path $LabRoot "tools\ahmad_tk_overlay.py"
$DistPath = Join-Path $LabRoot "dist"
$BuildPath = Join-Path $LabRoot "build"
$StaticData = Join-Path $RepoRoot "external_references\AuctionAnalyzer4.13.3\_decompiled\MapBidCalculator\MapBidCalculator\Models\StaticData.cs"

function Test-PyInstaller {
    & $PythonPath -m PyInstaller --version *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path $PythonPath)) {
    throw "Python not found: $PythonPath"
}
if (-not (Test-Path $Entry)) {
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
    "--windowed",
    "--name", $Name,
    "--distpath", $DistPath,
    "--workpath", $BuildPath,
    "--specpath", $BuildPath,
    "--paths", (Join-Path $LabRoot "tools"),
    "--paths", (Join-Path $LabRoot "src"),
    "--hidden-import", "ahmad_ref_engine"
)
if (-not $NoClean) {
    $Args += "--clean"
}
if ($OneFile) {
    $Args += "--onefile"
}
if (Test-Path $StaticData) {
    $Args += @(
        "--add-data",
        "$StaticData;external_references\AuctionAnalyzer4.13.3\_decompiled\MapBidCalculator\MapBidCalculator\Models"
    )
} else {
    Write-Host "Warning: StaticData.cs not found; exe will use fallback defaults." -ForegroundColor Yellow
    Write-Host "Missing: $StaticData" -ForegroundColor Yellow
}
$Args += $Entry

Write-Host "== Build Hero Ref UI exe ==" -ForegroundColor Cyan
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
Write-Host "UI-only package. It reads an existing latest_snapshot.json; use start_ahmad_live.ps1 for monitor + UI during development." -ForegroundColor Yellow
