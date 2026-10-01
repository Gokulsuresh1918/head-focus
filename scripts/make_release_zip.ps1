# Build a clean ZIP for GitHub Releases (no .venv, secrets, or local junk).
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\make_release_zip.ps1
# Output: dist\head-focus-<version>.zip  (version from git tag or "snapshot")

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$version = "snapshot"
if ($env:GITHUB_REF_NAME -match '^v(.+)$') {
    $version = $Matches[1]
} else {
    try {
        $tag = git describe --tags --exact-match 2>$null
        if ($tag) { $version = $tag.TrimStart("v") }
    } catch {}
}

$outDir = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zipPath = Join-Path $outDir "head-focus-$version.zip"

$excludeDirs = @(".venv", ".git", "dist", "build", "__pycache__", ".cursor", ".idea", ".vscode")
$excludeFiles = @("config.json", "check_camera.jpg", "face_landmarker.task", "*.pyc")

$staging = Join-Path $env:TEMP "head-focus-release-$version"
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

Get-ChildItem $Root -Force | ForEach-Object {
    if ($excludeDirs -contains $_.Name) { return }
    if ($_.Name -eq "dist") { return }
    Copy-Item $_.FullName -Destination (Join-Path $staging $_.Name) -Recurse -Force
}

@("config.json", "check_camera.jpg", "face_landmarker.task") | ForEach-Object {
    $p = Join-Path $staging $_
    if (Test-Path $p) { Remove-Item $p -Force }
}

Get-ChildItem $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath -Force
Remove-Item $staging -Recurse -Force

Write-Host "Created: $zipPath"
Write-Host "Upload this file to GitHub Releases for download-only users."
