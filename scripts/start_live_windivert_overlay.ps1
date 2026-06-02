param(
  [string]$LogDir = "data\logs\live",
  [string]$ProcessName = "BidKing.exe",
  [int[]]$ServerPort = @(10000),
  [int]$NTrials = 500,
  [int]$RoiTrials = 250,
  [double]$DebounceSeconds = 0.7,
  [double]$MinInferenceIntervalSeconds = 1.0,
  [switch]$PortOnly,
  [switch]$Restart
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = (Get-Command python).Source
$PythonwCommand = Get-Command pythonw -ErrorAction SilentlyContinue
$PythonWindowed = if ($PythonwCommand) { $PythonwCommand.Source } else { $Python }
$Monitor = Join-Path $Repo "scripts\run_windivert_live_monitor.py"
$Overlay = Join-Path $Repo "scripts\run_live_overlay.py"
$LogPath = Join-Path $Repo $LogDir
$LockPath = Join-Path $LogPath "monitor.lock"
$MonitorOut = Join-Path $LogPath "monitor.stdout.log"
$MonitorErr = Join-Path $LogPath "monitor.stderr.log"

$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltinRole]::Administrator
)

$MonitorArgs = @(
  $Monitor,
  "--log-dir", $LogPath,
  "--process-name", $ProcessName,
  "--n-trials", "$NTrials",
  "--roi-trials", "$RoiTrials",
  "--debounce-seconds", "$DebounceSeconds",
  "--min-inference-interval-seconds", "$MinInferenceIntervalSeconds"
)
foreach ($PortValue in $ServerPort) {
  $MonitorArgs += @("--server-port", "$PortValue")
}
if (-not $PortOnly) {
  $MonitorArgs += "--broad"
}

New-Item -ItemType Directory -Path $LogPath -Force | Out-Null

$MonitorProcesses = @(
  Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -like "python*" -and
    (
      $_.CommandLine -like "*run_windivert_live_monitor.py*" -or
      $_.CommandLine -like "*run_fatbeans_webhook_monitor.py*" -or
      $_.CommandLine -like "*run_fatbeans_live_monitor.py*"
    ) -and
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

Write-Host "BidKing WinDivert live monitor started." -ForegroundColor Green
Write-Host "LogDir:     $LogPath"
Write-Host "Process:    $ProcessName"
Write-Host "Mode:       $(if ($PortOnly) { 'port-filter' } else { 'broad-sniff + process-match' })"
Write-Host "ServerPort: $($ServerPort -join ',')"
if (-not $IsAdmin) {
  Write-Host "Warning: WinDivert usually requires an elevated/admin PowerShell." -ForegroundColor Yellow
}
Write-Host "If monitor.stderr.log says pydivert is missing, run: python -m pip install pydivert"
if ($MonitorProcesses) {
  Write-Host "Monitor:    already running (PID $($MonitorProcesses[0].ProcessId))"
}
if ($OverlayProcesses) {
  Write-Host "Overlay:    already running (PID $($OverlayProcesses[0].ProcessId))"
}
