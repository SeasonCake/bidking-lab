param(
  [string]$LogDir = "data\logs\live"
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LogPath = Join-Path $Repo $LogDir
$LockPath = Join-Path $LogPath "monitor.lock"

$Processes = Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -like "python*" -and
    $_.CommandLine -like "*run_fatbeans_live_monitor.py*"
  }

foreach ($Process in $Processes) {
  Stop-Process -Id $Process.ProcessId -Force
}

if (Test-Path $LockPath) {
  Remove-Item -LiteralPath $LockPath -Force
}

Write-Host "Stopped BidKing live monitor processes: $($Processes.Count)" -ForegroundColor Green
Write-Host "LogDir: $LogPath"
