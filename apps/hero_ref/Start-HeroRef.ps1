param(
    [string]$PythonPath = "",
    [string]$ProcessName = "BidKing.exe",
    [int[]]$ServerPort = @(10000),
    [switch]$BroadSniff,
    [switch]$IncludeLoopback,
    [switch]$KeepMonitorOnClose,
    [switch]$NoRestart,
    [switch]$NoAutoElevate
)

$ErrorActionPreference = "Stop"

$AppRoot = $PSScriptRoot
$ScriptsDir = Join-Path $AppRoot "scripts"
$LogDir = Join-Path $AppRoot "data\logs\live"
$LockPath = Join-Path $LogDir "monitor.lock"
$OverlayPidPath = Join-Path $LogDir "ahmad_overlay.pid"
$SnapshotPath = Join-Path $LogDir "latest_snapshot.json"
$HeroExe = Join-Path $AppRoot "BidKingHeroRef\BidKingHeroRef.exe"
$MonitorStart = Join-Path $ScriptsDir "start_live_windivert_overlay.ps1"
$ResolvePython = Join-Path $ScriptsDir "resolve_python.ps1"

function Get-CurrentPowerShellPath {
    try {
        $Current = Get-Process -Id $PID -ErrorAction Stop
        if ($Current.Path) {
            return $Current.Path
        }
    } catch {
    }
    $Pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($Pwsh) {
        return $Pwsh.Source
    }
    $PowerShell = Get-Command powershell -ErrorAction SilentlyContinue
    if ($PowerShell) {
        return $PowerShell.Source
    }
    throw "PowerShell executable not found for elevation"
}

function Get-MonitorLockPayload {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Test-PacketPython {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    & $Path -c "import pydivert, psutil" *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-Path -LiteralPath $HeroExe)) {
    throw "Hero Ref UI exe not found: $HeroExe"
}
if (-not (Test-Path -LiteralPath $MonitorStart)) {
    throw "Monitor starter not found: $MonitorStart"
}
if (-not (Test-Path -LiteralPath $ResolvePython)) {
    throw "Python resolver not found: $ResolvePython"
}

$RequiredTables = @("BidMap.txt", "Drop.txt", "Item.txt")
$TablesDir = Join-Path $AppRoot "data\raw\tables"
$MissingTables = @(
    foreach ($Name in $RequiredTables) {
        $Path = Join-Path $TablesDir $Name
        if (-not (Test-Path -LiteralPath $Path)) {
            $Name
        }
    }
)
if ($MissingTables.Count -gt 0) {
    Write-Host "Missing local game tables: $($MissingTables -join ', ')" -ForegroundColor Red
    Write-Host "This portable build needs data\raw\tables from the same local game/table version." -ForegroundColor Yellow
    Write-Host "Do not publish raw game tables unless you have permission." -ForegroundColor Yellow
    exit 1
}

$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltinRole]::Administrator
)

if (-not $IsAdmin -and -not $NoAutoElevate) {
    $ElevatedArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath,
        "-ProcessName", $ProcessName,
        "-NoAutoElevate"
    )
    if ($PythonPath) {
        $ElevatedArgs += @("-PythonPath", $PythonPath)
    }
    foreach ($PortValue in $ServerPort) {
        $ElevatedArgs += @("-ServerPort", "$PortValue")
    }
    if ($BroadSniff) {
        $ElevatedArgs += "-BroadSniff"
    }
    if ($IncludeLoopback) {
        $ElevatedArgs += "-IncludeLoopback"
    }
    if ($KeepMonitorOnClose) {
        $ElevatedArgs += "-KeepMonitorOnClose"
    }
    if ($NoRestart) {
        $ElevatedArgs += "-NoRestart"
    }
    Start-Process -FilePath (Get-CurrentPowerShellPath) -Verb RunAs -WindowStyle Hidden -WorkingDirectory $AppRoot -ArgumentList $ElevatedArgs
    Write-Host "WinDivert needs Administrator. Relaunched hidden elevated starter." -ForegroundColor Yellow
    return
}

. $ResolvePython
$Python = Resolve-BidKingPython -ExplicitPython $PythonPath -RequirePacket
if (-not (Test-PacketPython -Path $Python)) {
    Write-Host "Python packet dependencies are missing for: $Python" -ForegroundColor Red
    Write-Host "Install once:" -ForegroundColor Yellow
    Write-Host "  `"$Python`" -m pip install pydivert psutil" -ForegroundColor Yellow
    exit 1
}

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

$MonitorParams = @{
    LogDir = "data\logs\live"
    ProcessName = $ProcessName
    PythonPath = $Python
    ServerPort = $ServerPort
    NTrials = 500
    RoiTrials = 0
    FullShadowTrials = 20
    FastNTrials = 10
    FormalMode = "v3_practical"
    NoOverlay = $true
    NoAutoElevate = $true
}
if (-not $NoRestart) {
    $MonitorParams["Restart"] = $true
}
if ($BroadSniff) {
    $MonitorParams["BroadSniff"] = $true
} else {
    $MonitorParams["PortOnly"] = $true
}
if ($IncludeLoopback) {
    $MonitorParams["IncludeLoopback"] = $true
}
if ($KeepMonitorOnClose) {
    $MonitorParams["KeepMonitorOnOverlayClose"] = $true
}

Write-Host "== BidKing Hero Ref ==" -ForegroundColor Cyan
Write-Host "App:     $AppRoot"
Write-Host "Python:  $Python"
Write-Host "Mode:    WinDivert monitor + Hero Ref UI"
Write-Host ""

& $MonitorStart @MonitorParams
if ($LASTEXITCODE) {
    exit $LASTEXITCODE
}

$MonitorPid = $null
$Deadline = (Get-Date).AddSeconds(5)
while (-not $MonitorPid -and (Get-Date) -lt $Deadline) {
    $LockPayload = Get-MonitorLockPayload -Path $LockPath
    if ($LockPayload -and $LockPayload.pid) {
        $MonitorPid = [int]$LockPayload.pid
        break
    }
    Start-Sleep -Milliseconds 250
}

$HeroArgs = @("--snapshot", $SnapshotPath, "--load-existing")
if ($MonitorPid -and -not $KeepMonitorOnClose) {
    $HeroArgs += @(
        "--stop-pid-on-exit", "$MonitorPid",
        "--exit-when-pid-exits", "$MonitorPid",
        "--cleanup-lock-on-exit", $LockPath
    )
    Write-Host "Lifecycle: closing Hero Ref will stop monitor PID $MonitorPid"
} elseif ($KeepMonitorOnClose) {
    Write-Host "Lifecycle: Hero Ref will not stop monitor (-KeepMonitorOnClose)"
} else {
    Write-Host "Lifecycle: monitor lock not found; Hero Ref cannot stop monitor automatically." -ForegroundColor Yellow
}

$Hero = Start-Process -FilePath $HeroExe -WorkingDirectory $AppRoot -ArgumentList $HeroArgs -PassThru
if ($Hero -and $Hero.Id) {
    Set-Content -Path $OverlayPidPath -Value "$($Hero.Id)" -Encoding ascii
    Write-Host "Hero Ref: started (PID $($Hero.Id))" -ForegroundColor Green
}
