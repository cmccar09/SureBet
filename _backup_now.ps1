# Run this any time you want a rollback snapshot
# Usage:  .\_backup_now.ps1
#         .\_backup_now.ps1 -Label "before-big-change"

param([string]$Label = "")

$date  = Get-Date -Format "yyyy-MM-dd_HHmm"
$slug  = if ($Label) { "${date}_${Label}" } else { $date }
$dest  = Join-Path $PSScriptRoot "_backups\$slug"

New-Item -ItemType Directory -Path $dest -Force | Out-Null

$files = @(
    "_bpapi_patched.py",
    "frontend\src\App.js"
)

foreach ($f in $files) {
    $src = Join-Path $PSScriptRoot $f
    if (Test-Path $src) {
        Copy-Item $src $dest
        Write-Host "  backed up: $f"
    } else {
        Write-Warning "  not found: $f"
    }
}

Write-Host "`nSnapshot saved to: $dest"
