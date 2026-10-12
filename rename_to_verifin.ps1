<#
.SYNOPSIS
    VeriFin - Safe Folder Rename Tool for PowerShell
.DESCRIPTION
    Renames C:\D\Dev\Projects\fintel-ai to C:\D\Dev\Projects\VeriFin.
#>

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "               VeriFin - Project Root Folder Rename                   " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$parentDir = "C:\D\Dev\Projects"
$srcDir    = Join-Path $parentDir "fintel-ai"
$dstDir    = Join-Path $parentDir "VeriFin"

if (-not (Test-Path $srcDir)) {
    if (Test-Path $dstDir) {
        Write-Host "[SUCCESS] Directory has already been renamed to VeriFin!" -ForegroundColor Green
        return
    } else {
        Write-Host "[ERROR] Neither '$srcDir' nor '$dstDir' was found." -ForegroundColor Red
        return
    }
}

if (Test-Path $dstDir) {
    Write-Host "[ERROR] Target directory '$dstDir' already exists!" -ForegroundColor Red
    return
}

Write-Host "Renaming '$srcDir' -> '$dstDir'..." -ForegroundColor Yellow

try {
    # Move working directory away if currently in fintel-ai
    if ($PWD.Path.StartsWith($srcDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        Set-Location $parentDir
    }
    Rename-Item -Path $srcDir -NewName "VeriFin" -ErrorAction Stop
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "[SUCCESS] Successfully renamed project root to:" -ForegroundColor Green
    Write-Host "          $dstDir" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host "You can now open $dstDir in your editor." -ForegroundColor White
} catch {
    Write-Host ""
    Write-Host "[LOCKED] Could not rename folder: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please close VS Code / Antigravity, close any terminals open in fintel-ai, and re-run:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File C:\D\Dev\Projects\fintel-ai\rename_to_verifin.ps1" -ForegroundColor White
}
