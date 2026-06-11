$ErrorActionPreference = "SilentlyContinue"

$AppRoot = $PSScriptRoot
$LogDir = Join-Path $AppRoot "data\logs\live"
$OverlayPidPath = Join-Path $LogDir "ahmad_overlay.pid"
$LockPath = Join-Path $LogDir "monitor.lock"

if (Test-Path -LiteralPath $OverlayPidPath) {
    try {
        $OverlayPid = [int]((Get-Content -LiteralPath $OverlayPidPath -Raw).Trim())
        Stop-Process -Id $OverlayPid -Force
    } catch {
    }
    Remove-Item -LiteralPath $OverlayPidPath -Force
}

if (Test-Path -LiteralPath $LockPath) {
    try {
        $LockPayload = Get-Content -LiteralPath $LockPath -Raw | ConvertFrom-Json
        if ($LockPayload.pid) {
            Stop-Process -Id ([int]$LockPayload.pid) -Force
        }
    } catch {
    }
    Remove-Item -LiteralPath $LockPath -Force
}

Write-Host "Hero Ref UI and monitor stop requested."
