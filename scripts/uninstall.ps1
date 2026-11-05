<#
.SYNOPSIS
    Removes the AE MCP Bridge CEP extension (Windows).
    PlayerDebugMode keys are left untouched, since other unsigned extensions may rely on them.
#>
$ErrorActionPreference = "Stop"
$dst = Join-Path $env:APPDATA "Adobe\CEP\extensions\com.vslon.aemcp"
if (Test-Path $dst) {
    Remove-Item -Recurse -Force $dst
    Write-Host "[ok] removed $dst"
} else {
    Write-Host "nothing to remove ($dst not found)"
}
Write-Host "Remember to delete the 'after-effects' entry from your MCP client config."
