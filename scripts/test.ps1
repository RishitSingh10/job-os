<#
.SYNOPSIS
    Run the backend test suite (pytest) with coverage.
.EXAMPLE
    ./scripts/test.ps1
#>
[CmdletBinding()]
param([switch]$Cov)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

uv sync --group dev

if ($Cov) {
    uv run pytest --cov=core --cov=backend --cov=agents --cov-report=term-missing
} else {
    uv run pytest
}
