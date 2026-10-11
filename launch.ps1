param([switch]$SetupOnly, [switch]$NoBrowser, [switch]$ForcePortable)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$taskRoot = $PSScriptRoot
$taskRuntime = Join-Path $taskRoot '.runtime'
$taskTools = Join-Path $taskRoot 'tools'
$taskVenvPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
$taskLock = $null

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Executable" }
}

function Test-Command {
    param([string]$Executable, [string[]]$Arguments)
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments *> $null
    return $LASTEXITCODE -eq 0
}

function Get-WorkingPython {
    param([string]$Candidate)
    if (-not $Candidate -or -not (Test-Path -LiteralPath $Candidate)) { return $null }
    try {
        & $Candidate -c 'import sys,venv; assert (3,10) <= sys.version_info[:2] < (3,14)' 2>$null
        if ($LASTEXITCODE -eq 0) { return $Candidate }
    } catch {}
    return $null
}

function Get-Python {
    $taskLocalPython = Join-Path $taskTools 'python\python.exe'
    $taskFound = Get-WorkingPython $taskLocalPython
    if ($taskFound) { return $taskFound }
    if (-not $ForcePortable) {
        $taskCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($taskCommand -and $taskCommand.Source -notmatch 'WindowsApps') {
            $taskFound = Get-WorkingPython $taskCommand.Source
            if ($taskFound) { return $taskFound }
        }
        $taskLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
        if ($taskLauncher) {
            foreach ($taskVersion in @('3.13','3.12','3.11','3.10')) {
                try {
                    $taskCandidate = & $taskLauncher.Source "-$taskVersion" -c 'import sys; print(sys.executable)' 2>$null
                    if ($LASTEXITCODE -eq 0) {
                        $taskFound = Get-WorkingPython ([string]$taskCandidate)
                        if ($taskFound) { return $taskFound }
                    }
                } catch {}
            }
        }
    }
    Write-Host '[1/4] Installing Python 3.13.12 for this application...'
    $taskInstaller = Join-Path $taskRuntime 'python-3.13.12-amd64.exe'
    Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.13.12/python-3.13.12-amd64.exe' -OutFile $taskInstaller
    $taskSignature = Get-AuthenticodeSignature -LiteralPath $taskInstaller
    if ($taskSignature.Status -ne 'Valid' -or $taskSignature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
        throw 'Python installer signature could not be verified. Installation stopped.'
    }
    $taskPythonHome = Join-Path $taskTools 'python'
    $taskInstallerArguments = @('/quiet','InstallAllUsers=0','PrependPath=0','Include_launcher=0','AssociateFiles=0','Shortcuts=0','Include_test=0','Include_pip=1',"TargetDir=`"$taskPythonHome`"")
    $taskInstall = Start-Process -FilePath $taskInstaller -ArgumentList $taskInstallerArguments -WindowStyle Hidden -Wait -PassThru
    if ($taskInstall.ExitCode -notin @(0,3010)) { throw "Python installation failed ($($taskInstall.ExitCode))." }
    $taskFound = Get-WorkingPython $taskLocalPython
    if (-not $taskFound) { throw 'Python installation did not finish. Check .runtime for details.' }
    return $taskFound
}

function Get-FFmpeg {
    $taskPortable = Join-Path $taskTools 'ffmpeg'
    if (Test-Path -LiteralPath $taskPortable) {
        $taskInstalled = Get-ChildItem -LiteralPath $taskPortable -Filter ffmpeg.exe -Recurse -File | Select-Object -First 1
        if ($taskInstalled) {
            if (Test-Command $taskInstalled.FullName @('-version')) { return $taskInstalled.FullName }
        }
    }
    if (-not $ForcePortable) {
        $taskCommand = Get-Command ffmpeg.exe -ErrorAction SilentlyContinue
        if ($taskCommand) {
            if (Test-Command $taskCommand.Source @('-version')) { return $taskCommand.Source }
        }
    }
    Write-Host '[2/4] Downloading FFmpeg (first installation only)...'
    $taskZip = Join-Path $taskRuntime 'ffmpeg.zip'
    $taskHashText = (Invoke-WebRequest -UseBasicParsing -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.sha256').Content
    $taskExpectedHash = [regex]::Match([string]$taskHashText, '\b[0-9a-fA-F]{64}\b').Value
    if (-not $taskExpectedHash) { throw 'FFmpeg checksum could not be read.' }
    Invoke-WebRequest -UseBasicParsing -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile $taskZip
    if ((Get-FileHash -LiteralPath $taskZip -Algorithm SHA256).Hash -ne $taskExpectedHash) { throw 'FFmpeg archive checksum did not match. Run again to retry.' }
    Expand-Archive -LiteralPath $taskZip -DestinationPath $taskPortable -Force
    $taskInstalled = Get-ChildItem -LiteralPath $taskPortable -Filter ffmpeg.exe -Recurse -File | Select-Object -First 1
    if (-not $taskInstalled) { throw 'FFmpeg was not found in the downloaded archive.' }
    if (-not (Test-Command $taskInstalled.FullName @('-version'))) { throw 'FFmpeg could not start on this computer.' }
    return $taskInstalled.FullName
}

function Get-AppHealth {
    param([int]$Port)
    $taskClient = New-Object Net.Sockets.TcpClient
    try {
        $taskConnection = $taskClient.BeginConnect('127.0.0.1',$Port,$null,$null)
        if (-not $taskConnection.AsyncWaitHandle.WaitOne(150)) { return $null }
        $taskClient.EndConnect($taskConnection)
    } catch { return $null } finally { $taskClient.Close() }
    try {
        $taskHealth = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
        if ($taskHealth.app -eq 'tempo-studio' -and $taskHealth.workspace -eq $taskRoot) { return $taskHealth }
    } catch {}
    return $null
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'Windows 64-bit is required.' }
    New-Item -ItemType Directory -Force -Path $taskRuntime,$taskTools | Out-Null
    try { $taskLock = [IO.File]::Open((Join-Path $taskRuntime 'setup.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch { Write-Host 'Another Tempo Studio launcher is already setting up the application. Please wait.'; exit 0 }
    Set-Location -LiteralPath $taskRoot
    Write-Host 'TEMPO STUDIO - Automatic setup and launch'
    Write-Host 'First launch needs an internet connection. Later launches reuse the installation.'
    if ((Test-Path -LiteralPath $taskVenvPython) -and -not (Test-Command $taskVenvPython @('-c','import sys; assert sys.version_info >= (3,10)'))) {
        Write-Host 'Repairing the application Python environment...'
        $taskVenvFolder = [IO.Path]::GetFullPath((Join-Path $taskRoot '.venv'))
        $taskBackupFolder = [IO.Path]::GetFullPath((Join-Path $taskRuntime ('venv-backup-' + [Guid]::NewGuid().ToString('N'))))
        if ($taskVenvFolder -ne (Join-Path $taskRoot '.venv') -or -not $taskBackupFolder.StartsWith($taskRuntime + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Environment recovery path check failed.' }
        Move-Item -LiteralPath $taskVenvFolder -Destination $taskBackupFolder
        $taskOldMarker = Join-Path $taskRuntime 'requirements.sha256'
        if (Test-Path -LiteralPath $taskOldMarker) { Remove-Item -LiteralPath $taskOldMarker }
    }
    if (-not (Test-Path -LiteralPath $taskVenvPython)) {
        $taskPython = Get-Python
        Write-Host '[1/4] Creating isolated Python environment...'
        Invoke-Checked -Executable $taskPython -Arguments @('-m','venv',(Join-Path $taskRoot '.venv'))
    }
    # Python remembers its base location: report broken/copied environments clearly.
    Invoke-Checked -Executable $taskVenvPython -Arguments @('-c','import sys; assert sys.version_info >= (3,10)')
    $taskFFmpeg = Get-FFmpeg
    $env:PATH = (Split-Path -Parent $taskFFmpeg) + ';' + $env:PATH
    $taskRubberband = Join-Path $taskTools 'rubberband\rubberband-4.0.0-gpl-executable-windows\rubberband.exe'
    $taskRubberbandReady = $false
    if (Test-Path -LiteralPath $taskRubberband) {
        $taskRubberbandReady = Test-Command $taskRubberband @('--version')
    }
    if (-not $taskRubberbandReady) {
        Write-Host '[3/4] Installing Rubber Band R3...'
        & (Join-Path $taskRoot 'setup-rubberband.ps1')
        if (-not (Test-Command $taskRubberband @('--version'))) { throw 'Rubber Band could not start.' }
    }
    $taskRequirementsHash = (Get-FileHash -LiteralPath (Join-Path $taskRoot 'requirements.txt') -Algorithm SHA256).Hash
    $taskMarker = Join-Path $taskRuntime 'requirements.sha256'
    $taskInstallDependencies = -not (Test-Path -LiteralPath $taskMarker)
    $taskRepairDependencies = $false
    if (-not $taskInstallDependencies) { $taskInstallDependencies = (Get-Content -LiteralPath $taskMarker -Raw).Trim() -ne $taskRequirementsHash }
    if (-not $taskInstallDependencies) {
        $taskInstallDependencies = -not (Test-Command $taskVenvPython @('-c','import fastapi,uvicorn,multipart,flask,numpy; from app import app'))
        $taskRepairDependencies = $taskInstallDependencies
    }
    if ($taskInstallDependencies) {
        Write-Host '[4/4] Installing application dependencies...'
        $taskPipArguments = @('-m','pip','install','--disable-pip-version-check','-r',(Join-Path $taskRoot 'requirements.txt'))
        if ($taskRepairDependencies) { $taskPipArguments += '--force-reinstall' }
        Invoke-Checked -Executable $taskVenvPython -Arguments $taskPipArguments
        Invoke-Checked -Executable $taskVenvPython -Arguments @('-m','pip','check')
        Invoke-Checked -Executable $taskVenvPython -Arguments @('-c','from app import app; import flask,numpy')
        Set-Content -LiteralPath $taskMarker -Value $taskRequirementsHash -Encoding ASCII
    }
    if ($SetupOnly) { Write-Host 'Setup verified. Ready to launch.'; exit 0 }
    $taskPort = $null
    foreach ($taskCandidatePort in 8765..8785) {
        if (Get-AppHealth $taskCandidatePort) { $taskPort = $taskCandidatePort; break }
    }
    if (-not $taskPort) {
        foreach ($taskCandidatePort in 8765..8785) {
            $taskProbe = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,$taskCandidatePort)
            try { $taskProbe.Start(); $taskPort=$taskCandidatePort; break } catch {} finally { $taskProbe.Stop() }
        }
        if (-not $taskPort) { throw 'No free local port was found between 8765 and 8785.' }
        $taskServer = Start-Process -FilePath $taskVenvPython -ArgumentList @('-m','uvicorn','app:app','--host','127.0.0.1','--port',"$taskPort") -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRuntime 'server.log') -RedirectStandardError (Join-Path $taskRuntime 'server-error.log') -PassThru
        $taskServer.Refresh()
        @{pid=$taskServer.Id;startTicks="$($taskServer.StartTime.ToUniversalTime().Ticks)";port=$taskPort} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRuntime 'server.json') -Encoding UTF8
        $taskReady = $false
        for ($taskAttempt=0; $taskAttempt -lt 30; $taskAttempt++) {
            if (Get-AppHealth $taskPort) { $taskReady=$true; break }
            $taskServer.Refresh()
            if ($taskServer.HasExited) { break }
            Start-Sleep -Milliseconds 500
        }
        if (-not $taskReady) { throw 'Server did not become ready. See .runtime/server-error.log and run start.bat again.' }
    }
    $taskUrl = "http://127.0.0.1:$taskPort/"
    Write-Host "Ready: $taskUrl"
    Write-Host 'You can close this window. Use stop.bat to stop the application.'
    if (-not $NoBrowser) { Start-Process $taskUrl }
} catch {
    Write-Host "Setup/launch failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Check your internet connection and run start.bat again. The setup resumes completed steps.'
    exit 1
} finally {
    if ($taskLock) { $taskLock.Dispose() }
}
