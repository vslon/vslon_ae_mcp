<#
.SYNOPSIS
    Installs the AE MCP Bridge CEP extension for Adobe After Effects (Windows).

.DESCRIPTION
    1. Copies extension\com.vslon.aemcp to %APPDATA%\Adobe\CEP\extensions
    2. Enables unsigned CEP extensions (PlayerDebugMode=1 for CSXS.9 - CSXS.13, current user only)
    3. Prints the MCP client config snippet with absolute paths for this machine

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\install.ps1
#>
[CmdletBinding()]
param(
    [string]$Python = ""
)
$ErrorActionPreference = "Stop"

$repo   = Split-Path -Parent $PSScriptRoot
$src    = Join-Path $repo "extension\com.vslon.aemcp"
$dstDir = Join-Path $env:APPDATA "Adobe\CEP\extensions"
$dst    = Join-Path $dstDir "com.vslon.aemcp"
$server = Join-Path $repo "server\ae_mcp_server.py"

Write-Host "vslon_ae_mcp installer" -ForegroundColor Cyan

# 1. extension
New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
Copy-Item -Recurse -Force $src $dst
Write-Host "  [ok] extension -> $dst"

# 2. unsigned extensions
foreach ($v in 9..13) {
    $key = "HKCU:\Software\Adobe\CSXS.$v"
    New-Item -Force -Path $key | Out-Null
    Set-ItemProperty -Path $key -Name "PlayerDebugMode" -Value "1" -Type String
}
Write-Host "  [ok] PlayerDebugMode=1 for CSXS.9-13"

# 3. python
if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command py -ErrorAction SilentlyContinue }
    if ($cmd) { $Python = $cmd.Source }
}
if (-not $Python) {
    Write-Warning "Python 3 not found on PATH. Pass -Python <path to python.exe> or edit the config below."
    $Python = "python"
}

$cfg = [ordered]@{
    mcpServers = [ordered]@{
        "after-effects" = [ordered]@{ command = $Python; args = @($server) }
    }
} | ConvertTo-Json -Depth 5

Write-Host ""
Write-Host "Add this to your MCP client config (Claude Desktop: Settings > Developer > Edit Config):" -ForegroundColor Cyan
Write-Host $cfg
Write-Host ""
Write-Host "Then restart After Effects and your MCP client." -ForegroundColor Cyan
Write-Host "Check: Window > Extensions > AE MCP Bridge should say 'listening on 127.0.0.1:8765'."
