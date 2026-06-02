param(
  [string]$LogDir = "data\logs\live",
  [string]$ProcessName = "BidKing.exe",
  [string]$PythonPath = "",
  [int[]]$ServerPort = @(10000),
  [int]$NTrials = 500,
  [int]$RoiTrials = 250,
  [double]$DebounceSeconds = 0.7,
  [double]$MinInferenceIntervalSeconds = 1.0,
  [switch]$PortOnly,
  [switch]$KeepMonitorOnOverlayClose,
  [switch]$NoAutoElevate,
  [switch]$Restart
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Monitor = Join-Path $Repo "scripts\run_windivert_live_monitor.py"
$Overlay = Join-Path $Repo "scripts\run_live_overlay.py"
$LogPath = Join-Path $Repo $LogDir
$LockPath = Join-Path $LogPath "monitor.lock"
$MonitorOut = Join-Path $LogPath "monitor.stdout.log"
$MonitorErr = Join-Path $LogPath "monitor.stderr.log"

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

if (-not $IsAdmin -and -not $NoAutoElevate) {
  $ElevatedArgs = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $PSCommandPath,
    "-LogDir", $LogDir,
    "-ProcessName", $ProcessName,
    "-NTrials", "$NTrials",
    "-RoiTrials", "$RoiTrials",
    "-DebounceSeconds", "$DebounceSeconds",
    "-MinInferenceIntervalSeconds", "$MinInferenceIntervalSeconds",
    "-NoAutoElevate"
  )
  if ($PythonPath) {
    $ElevatedArgs += @("-PythonPath", $PythonPath)
  }
  foreach ($PortValue in $ServerPort) {
    $ElevatedArgs += @("-ServerPort", "$PortValue")
  }
  if ($PortOnly) {
    $ElevatedArgs += "-PortOnly"
  }
  if ($KeepMonitorOnOverlayClose) {
    $ElevatedArgs += "-KeepMonitorOnOverlayClose"
  }
  if ($Restart) {
    $ElevatedArgs += "-Restart"
  }
  $PowerShellPath = Get-CurrentPowerShellPath
  Start-Process -FilePath $PowerShellPath -Verb RunAs -WorkingDirectory $Repo -ArgumentList $ElevatedArgs
  Write-Host "WinDivert requires Administrator. Relaunched an elevated PowerShell for live monitor." -ForegroundColor Yellow
  return
}

function Test-PythonModules {
  param([string]$Candidate)
  if (-not $Candidate -or -not (Test-Path $Candidate)) {
    return $false
  }
  & $Candidate -c "import pydivert, psutil" *> $null
  return $LASTEXITCODE -eq 0
}

function Get-ProcessIdValue {
  param($Process)
  if (-not $Process) {
    return $null
  }
  if ($Process.PSObject.Properties.Name -contains "ProcessId" -and $Process.ProcessId) {
    return [int]$Process.ProcessId
  }
  if ($Process.PSObject.Properties.Name -contains "Id" -and $Process.Id) {
    return [int]$Process.Id
  }
  return $null
}

function Resolve-MonitorPython {
  param([string]$ExplicitPython)
  $Candidates = New-Object System.Collections.Generic.List[string]
  if ($ExplicitPython) {
    $Candidates.Add($ExplicitPython)
  }
  $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($PythonCommand) {
    $Candidates.Add($PythonCommand.Source)
  }
  $PyCommand = Get-Command py -ErrorAction SilentlyContinue
  if ($PyCommand) {
    $PyOutput = & $PyCommand.Source -0p 2>$null
    foreach ($Line in $PyOutput) {
      if ($Line -match '([A-Z]:\\.*python\.exe)') {
        $Candidates.Add($Matches[1])
      }
    }
  }
  $Candidates.Add("C:\Users\shenc\anaconda3\python.exe")
  $Candidates.Add("C:\Python313\python.exe")
  $Seen = @{}
  foreach ($Candidate in $Candidates) {
    if (-not $Candidate -or $Seen.ContainsKey($Candidate)) {
      continue
    }
    $Seen[$Candidate] = $true
    if (Test-PythonModules $Candidate) {
      return $Candidate
    }
  }
  if ($ExplicitPython) {
    return $ExplicitPython
  }
  if ($PythonCommand) {
    return $PythonCommand.Source
  }
  throw "python not found"
}

$Python = Resolve-MonitorPython $PythonPath
$PythonwCandidate = Join-Path (Split-Path -Parent $Python) "pythonw.exe"
$PythonWindowed = if (Test-Path $PythonwCandidate) { $PythonwCandidate } else { $Python }
$HasPacketDeps = Test-PythonModules $Python

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

$StartedMonitor = $null
if (-not $MonitorProcesses) {
  $StartedMonitor = Start-Process -FilePath $Python -WorkingDirectory $Repo -WindowStyle Hidden -PassThru -ArgumentList @(
    $MonitorArgs
  ) -RedirectStandardOutput $MonitorOut -RedirectStandardError $MonitorErr
} else {
  $StartedMonitor = $MonitorProcesses[0]
}
$StartedMonitorPid = Get-ProcessIdValue $StartedMonitor

if (-not $OverlayProcesses) {
  $OverlayArgs = @(
    $Overlay,
    "--snapshot", (Join-Path $LogPath "latest_snapshot.json")
  )
  if (-not $KeepMonitorOnOverlayClose -and $StartedMonitorPid) {
    $OverlayArgs += @(
      "--stop-pid-on-exit", "$StartedMonitorPid",
      "--cleanup-lock-on-exit", $LockPath
    )
  }
  Start-Process -FilePath $PythonWindowed -WorkingDirectory $Repo -ArgumentList $OverlayArgs
}

Write-Host "BidKing WinDivert live monitor started." -ForegroundColor Green
Write-Host "LogDir:     $LogPath"
Write-Host "Process:    $ProcessName"
Write-Host "Mode:       $(if ($PortOnly) { 'port-filter' } else { 'broad-sniff + process-match' })"
Write-Host "ServerPort: $($ServerPort -join ',')"
Write-Host "Python:     $Python"
if (-not $IsAdmin) {
  Write-Host "Warning: WinDivert usually requires an elevated/admin PowerShell." -ForegroundColor Yellow
}
if (-not $HasPacketDeps) {
  Write-Host "Warning: selected Python cannot import pydivert/psutil." -ForegroundColor Yellow
  Write-Host "Install with: `"$Python`" -m pip install -e `"$Repo[packet]`""
}
Write-Host "If monitor.stderr.log says pydivert is missing, run: `"$Python`" -m pip install pydivert"
if ($MonitorProcesses) {
  Write-Host "Monitor:    already running (PID $($MonitorProcesses[0].ProcessId))"
}
if ($OverlayProcesses) {
  Write-Host "Overlay:    already running (PID $($OverlayProcesses[0].ProcessId))"
}
if (-not $KeepMonitorOnOverlayClose -and $StartedMonitorPid) {
  Write-Host "Lifecycle:  closing overlay will stop monitor PID $StartedMonitorPid"
}
