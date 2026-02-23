# YGGDRASIL — Install git hooks (Windows PowerShell)
# Usage: .\hooks\install.ps1

$hookSrc = Join-Path $PSScriptRoot "pre-commit"
$hookDst = Join-Path (git rev-parse --git-dir) "hooks" "pre-commit"

Copy-Item $hookSrc $hookDst -Force
Write-Host "[winter-tree] Hook installe: $hookDst" -ForegroundColor Green
Write-Host "[winter-tree] winter-tree.json se mettra a jour a chaque commit." -ForegroundColor Cyan
