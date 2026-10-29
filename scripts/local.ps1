param(
    [ValidateSet('Start', 'Stop', 'Status')]
    [string]$Action = 'Start',
    [ValidateRange(1024, 65535)]
    [int]$HttpPort = 8000,
    [ValidateRange(1024, 65535)]
    [int]$DatabasePort = 5432,
    [ValidatePattern('^winddesk-local(?:-[a-z0-9-]+)?$')]
    [string]$Project = 'winddesk-local'
)

$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$taskDockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$taskDocker = if ($taskDockerCommand) { $taskDockerCommand.Source } else {
    Join-Path $env:ProgramFiles 'Docker\Docker\resources\bin\docker.exe'
}
if (-not (Test-Path -LiteralPath $taskDocker)) { throw 'Install Docker Desktop with Linux containers first.' }
$taskCompose = @('compose', '--project-name', $Project, '--file', (Join-Path $taskRoot 'compose.yaml'))
$taskKeys = @('GRID_HTTP_PORT', 'GRID_POSTGRES_PORT', 'GRID_BUILD_SHA', 'GRID_IMAGE_TAG')
$taskPrevious = @{}
foreach ($taskKey in $taskKeys) { $taskPrevious[$taskKey] = [Environment]::GetEnvironmentVariable($taskKey, 'Process') }

function Invoke-TaskDocker {
    param([string[]]$DockerArguments)
    & $taskDocker @DockerArguments
    if ($LASTEXITCODE -ne 0) { throw 'Docker command failed. Check Docker Desktop, available ports, and the output above.' }
}

try {
    $env:GRID_HTTP_PORT = [string]$HttpPort
    $env:GRID_POSTGRES_PORT = [string]$DatabasePort
    $env:GRID_IMAGE_TAG = $Project
    $env:GRID_BUILD_SHA = 'local'
    $taskGitCommand = Get-Command git -ErrorAction SilentlyContinue
    $taskGit = if ($env:GRID_GIT_EXECUTABLE) { $env:GRID_GIT_EXECUTABLE } elseif ($taskGitCommand) { $taskGitCommand.Source } else { $null }
    if ($taskGit -and (Test-Path -LiteralPath $taskGit)) {
        $taskRevision = & $taskGit -C $taskRoot rev-parse --verify HEAD 2>$null
        if ($LASTEXITCODE -eq 0) { $env:GRID_BUILD_SHA = $taskRevision.Trim() }
    }
    $taskEngine = & $taskDocker info --format '{{.OSType}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or $taskEngine -ne 'linux') { throw 'Start Docker Desktop in Linux-container mode, then run this command again.' }

    # A checkout must never control another folder's project with the same name.
    $taskIds = @(Invoke-TaskDocker -DockerArguments @('ps', '--all', '--filter', ('label=com.docker.compose.project=' + $Project), '--quiet'))
    foreach ($taskId in $taskIds) {
        $taskDetails = (Invoke-TaskDocker -DockerArguments @('inspect', $taskId)) | ConvertFrom-Json
        $taskOwner = $taskDetails[0].Config.Labels.'com.docker.compose.project.working_dir'
        if (-not $taskOwner -or [IO.Path]::GetFullPath($taskOwner) -ne $taskRoot) {
            throw 'This project name belongs to another checkout. Choose a new -Project winddesk-local-NAME.'
        }
    }

    if ($Action -eq 'Stop') {
        Invoke-TaskDocker -DockerArguments ($taskCompose + @('stop', '--timeout', '15', 'web', 'postgres'))
        Write-Output 'Local services stopped. The database volume is retained.'
    } elseif ($Action -eq 'Status') {
        Invoke-TaskDocker -DockerArguments ($taskCompose + @('ps', '--all'))
    } else {
        Invoke-TaskDocker -DockerArguments ($taskCompose + @('up', '--build', '--detach', '--wait', '--wait-timeout', '180', 'web'))
        $taskUrl = 'http://127.0.0.1:' + $HttpPort
        $taskDeadline = [DateTime]::UtcNow.AddSeconds(60)
        $taskReady = $null
        do {
            try { $taskReady = Invoke-RestMethod -Uri ($taskUrl + '/health/ready') -TimeoutSec 5 } catch { $taskReady = $null }
            if ($taskReady -and $taskReady.status -eq 'ready') { break }
            if ([DateTime]::UtcNow -ge $taskDeadline) { throw 'The web process is running but its dataset is not ready. Inspect docker compose logs.' }
            Start-Sleep -Seconds 1
        } while ($true)
        Write-Output ('Workbench ready: ' + $taskUrl)
        Write-Output ('Accepted dataset: ' + $taskReady.release_id)
    }
} finally {
    foreach ($taskKey in $taskKeys) { [Environment]::SetEnvironmentVariable($taskKey, $taskPrevious[$taskKey], 'Process') }
}
