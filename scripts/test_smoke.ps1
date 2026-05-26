param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs
)

python -m pytest -q -m "not slow" @PytestArgs
exit $LASTEXITCODE
