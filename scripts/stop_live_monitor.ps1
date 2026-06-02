param(
  [string]$LogDir = "data\logs\live"
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LogPath = Join-Path $Repo $LogDir
$LockPath = Join-Path $LogPath "monitor.lock"

$MonitorProcesses = @(
  Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -like "python*" -and
    (
      $_.CommandLine -like "*run_fatbeans_live_monitor.py*" -or
      $_.CommandLine -like "*run_fatbeans_webhook_monitor.py*" -or
      $_.CommandLine -like "*run_windivert_live_monitor.py*"
    )
  }
)
$OverlayProcesses = @(
  Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -like "python*" -and
    $_.CommandLine -like "*run_live_overlay.py*"
  }
)

foreach ($Process in @($MonitorProcesses + $OverlayProcesses)) {
  Stop-Process -Id $Process.ProcessId -Force
}

if (Test-Path $LockPath) {
  Remove-Item -LiteralPath $LockPath -Force
}

Write-Host "Stopped BidKing live monitor processes: $($MonitorProcesses.Count)" -ForegroundColor Green
Write-Host "Stopped BidKing overlay processes: $($OverlayProcesses.Count)" -ForegroundColor Green
Write-Host "LogDir: $LogPath"
