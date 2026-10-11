$ErrorActionPreference = 'Stop'
$taskRecordPath = Join-Path $PSScriptRoot '.runtime\server.json'
if (-not (Test-Path -LiteralPath $taskRecordPath)) { Write-Host 'No launcher-managed server found.'; exit 0 }
$taskRecord = Get-Content -LiteralPath $taskRecordPath -Raw | ConvertFrom-Json
$taskServer = Get-Process -Id $taskRecord.pid -ErrorAction SilentlyContinue
if (-not $taskServer) { Write-Host 'Tempo Studio is already stopped.'; exit 0 }
$taskCommand = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskServer.Id)"
$taskExpectedPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if ("$($taskServer.StartTime.ToUniversalTime().Ticks)" -ne $taskRecord.startTicks -or $taskCommand.ExecutablePath -ne $taskExpectedPython -or $taskCommand.CommandLine -notmatch '-m uvicorn app:app') {
    throw 'Process identity did not match. No process was stopped.'
}
# Windows venv python is a redirector: its child runs the actual server.
$taskChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($taskServer.Id)"
foreach ($taskChild in $taskChildren) {
    $taskPortPattern = '--port\s+' + [regex]::Escape([string]$taskRecord.port) + '(\s|$)'
    if ($taskChild.CommandLine -match '-m uvicorn app:app' -and $taskChild.CommandLine -match $taskPortPattern) {
        Stop-Process -Id $taskChild.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
Stop-Process -Id $taskServer.Id -Force -ErrorAction SilentlyContinue
Write-Host 'Tempo Studio stopped.'
