param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $Repo "scripts\resolve_python.ps1")
$Python = Resolve-BidKingPython

& $Python -m pytest -q -m "not slow" @PytestArgs
exit $LASTEXITCODE
