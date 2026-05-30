param(
  [string]$WatchDir = "C:\Users\shenc\Desktop\bid_king_packages",
  [string]$LogDir = "data\logs\live",
  [int]$NTrials = 500,
  [int]$RoiTrials = 250,
  [double]$StableSeconds = 1.0,
  [switch]$ProcessExisting
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = "python"
$Monitor = Join-Path $Repo "scripts\run_fatbeans_live_monitor.py"
$Overlay = Join-Path $Repo "scripts\run_live_overlay.py"
$LogPath = Join-Path $Repo $LogDir
$MonitorArgs = @(
  $Monitor,
  "--watch-dir", $WatchDir,
  "--log-dir", $LogPath,
  "--n-trials", "$NTrials",
  "--roi-trials", "$RoiTrials",
  "--stable-seconds", "$StableSeconds"
)
if (-not $ProcessExisting) {
  $MonitorArgs += "--ignore-existing"
}

New-Item -ItemType Directory -Path $LogPath -Force | Out-Null

Start-Process -FilePath $Python -WorkingDirectory $Repo -WindowStyle Hidden -ArgumentList @(
  $MonitorArgs
)

Start-Process -FilePath $Python -WorkingDirectory $Repo -ArgumentList @(
  $Overlay,
  "--snapshot", (Join-Path $LogPath "latest_snapshot.json")
)

Write-Host "BidKing live monitor started." -ForegroundColor Green
Write-Host "WatchDir: $WatchDir"
Write-Host "LogDir:   $LogPath"
