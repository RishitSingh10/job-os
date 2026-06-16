<#
.SYNOPSIS
    Run the Job OS backend in development mode with autoreload.
.DESCRIPTION
    Ensures dependencies are installed via uv, then launches uvicorn against the
    FastAPI app factory. Host/port come from the environment (.env) with defaults.
.EXAMPLE
    ./scripts/dev.ps1
#>
[CmdletBinding()]
param(
    [string]$AppHost = $env:JOBOS_HOST,
    [int]$Port = $(if ($env:JOBOS_PORT) { [int]$env:JOBOS_PORT } else { 8000 })
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $AppHost) { $AppHost = "127.0.0.1" }

Write-Host "Syncing dependencies (uv sync)..." -ForegroundColor Cyan
uv sync

Write-Host "Starting Job OS backend on http://${AppHost}:${Port} ..." -ForegroundColor Green
uv run uvicorn backend.main:app --reload --host $AppHost --port $Port
