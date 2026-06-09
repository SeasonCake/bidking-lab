param(
    [string]$PythonPath = "C:\Python313\python.exe",
    [string]$Snapshot = "",
    [int]$WaitMonitorLockSeconds = 5,
    [switch]$KeepMonitorOnClose,
    [switch]$LoadExisting,
    [switch]$NoAutoElevate,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

$LabRoot = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $LabRoot "..\..")
if (-not $Snapshot) {
    $Snapshot = Join-Path $RepoRoot "data\logs\live\latest_snapshot.json"
}
$LogPath = Join-Path $RepoRoot "data\logs\live"
$LockPath = Join-Path $RepoRoot "data\logs\live\monitor.lock"
$OverlayPidPath = Join-Path $LogPath "ahmad_overlay.pid"

$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltinRole]::Administrator
)

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

if ($Restart) {
    Get-CimInstance Win32_Process |
        Where-Object {
            (
                $_.CommandLine -like "*ahmad_tk_overlay.py*" -or
                $_.CommandLine -like "*BidKingHeroRef.exe*"
            ) -and
            $_.ProcessId -ne $PID
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force
        }
    if (Test-Path $OverlayPidPath) {
        try {
            $OldPid = [int]((Get-Content -LiteralPath $OverlayPidPath -Raw).Trim())
            Stop-Process -Id $OldPid -Force -ErrorAction SilentlyContinue
        } catch {
        }
        Remove-Item -LiteralPath $OverlayPidPath -Force -ErrorAction SilentlyContinue
    }
}

$OverlayArgs = @(
    (Join-Path $LabRoot "tools\ahmad_tk_overlay.py"),
    "--snapshot", $Snapshot
)
if ($LoadExisting) {
    $OverlayArgs += "--load-existing"
}

function Get-MonitorLockPayload {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

if (-not $KeepMonitorOnClose) {
    $LockPayload = Get-MonitorLockPayload -Path $LockPath
    $Deadline = (Get-Date).AddSeconds([Math]::Max(0, $WaitMonitorLockSeconds))
    while (-not $LockPayload -and (Get-Date) -lt $Deadline) {
        Start-Sleep -Milliseconds 250
        $LockPayload = Get-MonitorLockPayload -Path $LockPath
    }
    if ($LockPayload -and $LockPayload.pid) {
        $MonitorPid = [int]$LockPayload.pid
        if (-not $IsAdmin -and -not $NoAutoElevate) {
            $ElevatedArgs = @(
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", $PSCommandPath,
                "-PythonPath", $PythonPath,
                "-Snapshot", $Snapshot,
                "-WaitMonitorLockSeconds", "$WaitMonitorLockSeconds",
                "-NoAutoElevate"
            )
            if ($LoadExisting) {
                $ElevatedArgs += "-LoadExisting"
            }
            if ($Restart) {
                $ElevatedArgs += "-Restart"
            }
            $PowerShellPath = Get-CurrentPowerShellPath
            Start-Process -FilePath $PowerShellPath -Verb RunAs -WindowStyle Hidden -WorkingDirectory $RepoRoot -ArgumentList $ElevatedArgs
            Write-Host "Hero Ref needs Administrator to stop monitor PID $MonitorPid on close. Relaunched elevated." -ForegroundColor Yellow
            return
        }
        $OverlayArgs += @(
            "--stop-pid-on-exit", "$MonitorPid",
            "--exit-when-pid-exits", "$MonitorPid",
            "--cleanup-lock-on-exit", $LockPath
        )
        Write-Host "Lifecycle: closing Hero Ref will stop monitor PID $MonitorPid"
    } elseif (Test-Path $LockPath) {
        Write-Host "Lifecycle: monitor.lock exists but could not be parsed; Hero Ref will not stop monitor automatically." -ForegroundColor Yellow
    } else {
        Write-Host "Lifecycle: monitor.lock not found after waiting ${WaitMonitorLockSeconds}s; Hero Ref will not stop monitor automatically." -ForegroundColor Yellow
    }
} elseif ($KeepMonitorOnClose) {
    Write-Host "Lifecycle: Hero Ref will not stop monitor (-KeepMonitorOnClose)"
}

New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
$PythonWindowed = Join-Path (Split-Path -Parent $PythonPath) "pythonw.exe"
if (-not (Test-Path $PythonWindowed)) {
    $PythonWindowed = $PythonPath
}

$StartedOverlay = Start-Process -FilePath $PythonWindowed -WorkingDirectory $RepoRoot -ArgumentList $OverlayArgs -PassThru
if ($StartedOverlay -and $StartedOverlay.Id) {
    Set-Content -Path $OverlayPidPath -Value "$($StartedOverlay.Id)" -Encoding ascii
}
Start-Sleep -Milliseconds 800
$Alive = $false
if ($StartedOverlay -and $StartedOverlay.Id) {
    try {
        $null = Get-Process -Id $StartedOverlay.Id -ErrorAction Stop
        $Alive = $true
    } catch {
    }
}
if (-not $Alive) {
    Write-Host "Hero Ref failed to stay running." -ForegroundColor Red
    Write-Host "Retry foreground for traceback:" -ForegroundColor Yellow
    Write-Host "  & `"$PythonPath`" $($OverlayArgs -join ' ')" -ForegroundColor Yellow
    exit 1
}
Write-Host "Hero Ref:   started (PID $($StartedOverlay.Id))"
Write-Host "Snapshot:   $Snapshot"
