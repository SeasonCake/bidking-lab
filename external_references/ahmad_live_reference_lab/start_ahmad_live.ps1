param(
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$ProcessName = "BidKing.exe",
    [int[]]$ServerPort = @(10000),
    [int]$NTrials = 500,
    [int]$RoiTrials = 0,
    [int]$FullShadowTrials = 20,
    [int]$FastNTrials = 10,
    [ValidateSet("v3_practical", "v2")]
    [string]$FormalMode = "v3_practical",
    [ValidateSet("engineering", "portable", "public-safe", "stable", "public_safe")]
    [string]$DiagnosticProfile = "engineering",
    [switch]$BroadSniff,
    [switch]$IncludeLoopback,
    [switch]$KeepMonitorOnClose,
    [switch]$ShowTaskbar,
    [switch]$NoAutoElevate,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$LabRoot = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $LabRoot "..\..")
$MonitorStart = Join-Path $RepoRoot "scripts\start_live_windivert_overlay.ps1"
$HeroStart = Join-Path $LabRoot "start_ahmad_overlay.ps1"

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

$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltinRole]::Administrator
)

if (-not $IsAdmin -and -not $NoAutoElevate) {
    $ElevatedArgs = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath,
        "-PythonPath", $PythonPath,
        "-ProcessName", $ProcessName,
        "-NTrials", "$NTrials",
        "-RoiTrials", "$RoiTrials",
        "-FullShadowTrials", "$FullShadowTrials",
        "-FastNTrials", "$FastNTrials",
        "-FormalMode", $FormalMode,
        "-DiagnosticProfile", $DiagnosticProfile,
        "-NoAutoElevate"
    )
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
    if ($ShowTaskbar) {
        $ElevatedArgs += "-ShowTaskbar"
    }
    if ($NoRestart) {
        $ElevatedArgs += "-NoRestart"
    }
    Start-Process -FilePath (Get-CurrentPowerShellPath) -Verb RunAs -WindowStyle Hidden -WorkingDirectory $RepoRoot -ArgumentList $ElevatedArgs
    Write-Host "WinDivert requires Administrator. Relaunched Hero Ref live starter with UAC." -ForegroundColor Yellow
    return
}

$RestartMonitor = -not $NoRestart
$MonitorParams = @{
    PythonPath = $PythonPath
    ProcessName = $ProcessName
    ServerPort = $ServerPort
    NTrials = $NTrials
    RoiTrials = $RoiTrials
    FullShadowTrials = $FullShadowTrials
    FastNTrials = $FastNTrials
    FormalMode = $FormalMode
    NoOverlay = $true
    NoAutoElevate = $true
}
if ($RestartMonitor) {
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

Write-Host "== Hero Ref live starter ==" -ForegroundColor Cyan
Write-Host "Repo:       $RepoRoot"
Write-Host "Python:     $PythonPath"
Write-Host "UI:         Hero Ref only"
Write-Host "Diagnostic: $DiagnosticProfile"
Write-Host ""

& $MonitorStart @MonitorParams
if ($LASTEXITCODE) {
    exit $LASTEXITCODE
}

$HeroParams = @{
    PythonPath = $PythonPath
    DiagnosticProfile = $DiagnosticProfile
}
if ($RestartMonitor) {
    $HeroParams["Restart"] = $true
}
if ($KeepMonitorOnClose) {
    $HeroParams["KeepMonitorOnClose"] = $true
}
if ($ShowTaskbar) {
    $HeroParams["ShowTaskbar"] = $true
}

& $HeroStart @HeroParams
