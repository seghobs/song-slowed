$ErrorActionPreference = 'Stop'
$taskTools = Join-Path $PSScriptRoot 'tools'
$taskZip = Join-Path $taskTools 'rubberband.zip'
$taskDestination = Join-Path $taskTools 'rubberband'
New-Item -ItemType Directory -Force -Path $taskTools | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri 'https://breakfastquay.com/files/releases/rubberband-4.0.0-gpl-executable-windows.zip' -OutFile $taskZip
$taskHash = (Get-FileHash -LiteralPath $taskZip -Algorithm SHA256).Hash
if ($taskHash -ne 'F2D47FC64DBB42F6CC62EDF7933AC4FA89D8F0EF8B9CF97B6AFC263A7FE05644') {
    throw 'Rubber Band archive checksum did not match. Installation stopped.'
}
Expand-Archive -LiteralPath $taskZip -DestinationPath $taskDestination -Force
Write-Host 'Rubber Band 4.0.0 R3 installed. License: tools/rubberband/rubberband-4.0.0-gpl-executable-windows/COPYING.txt'
