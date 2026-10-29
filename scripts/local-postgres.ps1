param(
    [ValidateSet('Start', 'Stop', 'Status')]
    [string]$Action = 'Status'
)

$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This helper controls the prepared Windows-only test cluster.' }
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskData = Join-Path $taskRoot '.cache\postgres\data'
$taskBinary = Join-Path $taskRoot '.tools\pgsql\bin\pg_ctl.exe'
$taskLogs = Join-Path $taskRoot '.cache\postgres'
if (-not (Test-Path -LiteralPath $taskBinary) -or -not (Test-Path -LiteralPath (Join-Path $taskData 'PG_VERSION'))) {
    throw 'Prepared portable PostgreSQL cluster not found. Use Docker Compose for a fresh checkout.'
}
if (-not ([System.IO.Path]::GetFullPath($taskData)).StartsWith($taskRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'PostgreSQL data directory must remain inside this workspace.'
}
if ($Action -eq 'Status') {
    & $taskBinary status -D $taskData
    exit $LASTEXITCODE
}
$taskArguments = if ($Action -eq 'Start') {
    @('start', '-D', ('"' + $taskData + '"'), '-l', ('"' + (Join-Path $taskLogs 'server.log') + '"'),
      '-o', '"-h 127.0.0.1 -p 5432 -c timezone=UTC"', '-w', '-t', '30')
} else {
    @('stop', '-D', ('"' + $taskData + '"'), '-m', 'fast', '-w', '-t', '30')
}
$taskProcess = Start-Process -FilePath $taskBinary -ArgumentList $taskArguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $taskLogs 'control.out') -RedirectStandardError (Join-Path $taskLogs 'control.err')
if (-not $taskProcess.WaitForExit(40000)) { throw 'PostgreSQL control timed out; inspect .cache/postgres/control.err.' }
$taskProcess.Refresh()
if ($taskProcess.ExitCode -ne 0) { throw 'PostgreSQL control failed; inspect .cache/postgres/control.err.' }
Write-Output ('Workspace PostgreSQL action completed: ' + $Action)
exit 0
