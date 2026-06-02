param(
  [string]$WatchDir = "C:\Users\shenc\Desktop\bid_king_packages",
  [string]$LogDir = "data\logs\live",
  [int]$NTrials = 500,
  [int]$RoiTrials = 250,
  [double]$StableSeconds = 1.0,
  [double]$ProcessDelaySeconds = 1.5,
  [switch]$ProcessExisting,
  [switch]$ReprocessExisting,
  [switch]$Restart
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = (Get-Command python).Source
$PythonwCommand = Get-Command pythonw -ErrorAction SilentlyContinue
$PythonWindowed = if ($PythonwCommand) { $PythonwCommand.Source } else { $Python }
$Monitor = Join-Path $Repo "scripts\run_fatbeans_live_monitor.py"
$Overlay = Join-Path $Repo "scripts\run_live_overlay.py"
$LogPath = Join-Path $Repo $LogDir
$LockPath = Join-Path $LogPath "monitor.lock"
$MonitorOut = Join-Path $LogPath "monitor.stdout.log"
$MonitorErr = Join-Path $LogPath "monitor.stderr.log"
$MonitorArgs = @(
  $Monitor,
  "--watch-dir", $WatchDir,
  "--log-dir", $LogPath,
  "--n-trials", "$NTrials",
  "--roi-trials", "$RoiTrials",
  "--stable-seconds", "$StableSeconds",
  "--process-delay-seconds", "$ProcessDelaySeconds"
)
if ($ReprocessExisting) {
  $MonitorArgs += "--reprocess-existing-once"
}
if (-not $ProcessExisting -and -not $ReprocessExisting) {
  $MonitorArgs += "--ignore-existing"
}

New-Item -ItemType Directory -Path $LogPath -Force | Out-Null

$MonitorProcesses = @(
  Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -like "python*" -and
    $_.CommandLine -like "*run_fatbeans_live_monitor.py*" -and
    $_.CommandLine -like "*$LogPath*"
  }
)
$OverlayProcesses = @(
  Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -like "python*" -and
    $_.CommandLine -like "*run_live_overlay.py*" -and
    $_.CommandLine -like "*latest_snapshot.json*"
  }
)

if ($Restart) {
  foreach ($Process in @($MonitorProcesses + $OverlayProcesses)) {
    Stop-Process -Id $Process.ProcessId -Force
  }
  $MonitorProcesses = @()
  $OverlayProcesses = @()
  if (Test-Path $LockPath) {
    Remove-Item -LiteralPath $LockPath -Force
  }
}

if ((Test-Path $LockPath) -and -not $MonitorProcesses) {
  Remove-Item -LiteralPath $LockPath -Force
}

if (-not $MonitorProcesses) {
  Start-Process -FilePath $Python -WorkingDirectory $Repo -WindowStyle Hidden -ArgumentList @(
    $MonitorArgs
  ) -RedirectStandardOutput $MonitorOut -RedirectStandardError $MonitorErr
}

if (-not $OverlayProcesses) {
  Start-Process -FilePath $PythonWindowed -WorkingDirectory $Repo -ArgumentList @(
    $Overlay,
    "--snapshot", (Join-Path $LogPath "latest_snapshot.json")
  )
}

Write-Host "BidKing live monitor started." -ForegroundColor Green
Write-Host "WatchDir: $WatchDir"
Write-Host "LogDir:   $LogPath"
Write-Host "Delay:    $ProcessDelaySeconds sec between processed files"
if ($ReprocessExisting) {
  Write-Host "Replay:   existing files will be reprocessed once"
}
if ($MonitorProcesses) {
  Write-Host "Monitor:  already running (PID $($MonitorProcesses[0].ProcessId))"
}
if ($OverlayProcesses) {
  Write-Host "Overlay:  already running (PID $($OverlayProcesses[0].ProcessId))"
}
