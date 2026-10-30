<#
.SYNOPSIS
  Package skills/<name>/ into WorkBuddy-uploadable .zip skill packages.

.DESCRIPTION
  Produces two layouts so an uploader that expects either convention works:
    dist/<name>.zip         -> SKILL.md at the archive root   (default upload)
    dist/<name>-folder.zip  -> <name>/SKILL.md inside a folder (fallback)

  Excludes caches, bytecode, env files and logs. Never copies credentials:
  the skill reads its key from BAOLIANGXIA_AGENT_GATEWAY_API_KEY at runtime.

  WorkBuddy rejects a package whose version is not strictly greater than the
  version already published, so pass -Version to stamp a new one without
  hand-editing the archive.

.EXAMPLE
  pwsh -NoProfile -File tools/pack-workbuddy-skill.ps1

.EXAMPLE
  pwsh -NoProfile -File tools/pack-workbuddy-skill.ps1 -Version 1.0.2
#>
[CmdletBinding()]
param(
    [string]$SkillDir = (Join-Path $PSScriptRoot '..\skills\baoliangxia-skills'),
    [string]$OutDir = (Join-Path $PSScriptRoot '..\dist'),
    [string]$Name = '',
    [string]$Version = '',
    [double]$MaxMB = 3
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

$SkillDir = [System.IO.Path]::GetFullPath($SkillDir)
$OutDir = [System.IO.Path]::GetFullPath($OutDir)

if (-not (Test-Path -LiteralPath (Join-Path $SkillDir 'SKILL.md'))) {
    throw "SKILL.md not found in $SkillDir"
}

# The platform identifies a skill by the frontmatter name, so the archive name
# and the wrapper folder must follow it rather than a hardcoded string.
if (-not $Name) {
    $fmText = [System.IO.File]::ReadAllText((Join-Path $SkillDir 'SKILL.md'), [System.Text.Encoding]::UTF8)
    $m = [regex]::Match($fmText, '(?m)^name:\s*(\S+)\s*$')
    if (-not $m.Success) { throw "frontmatter 'name:' not found in SKILL.md; pass -Name explicitly" }
    $Name = $m.Groups[1].Value
}
Write-Output "SKILL_NAME=$Name"

$excludeDirs = @('__pycache__', '.git', '.idea', 'node_modules', '.venv', 'venv', '.pytest_cache')
$excludeFiles = @('*.pyc', '*.pyo', '.env', '.env.*', '*.log', '.DS_Store', 'Thumbs.db')

function New-Stage {
    param([string]$Path)
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    Get-ChildItem -LiteralPath $SkillDir -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Path -Recurse -Force
    }
    foreach ($d in $excludeDirs) {
        Get-ChildItem -LiteralPath $Path -Recurse -Force -Directory -Filter $d -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force
    }
    foreach ($f in $excludeFiles) {
        Get-ChildItem -LiteralPath $Path -Recurse -Force -File -Filter $f -ErrorAction SilentlyContinue |
            Remove-Item -Force
    }
}

# Rewrite the version line in a staged copy without touching the source file.
# Uses UTF-8 without BOM: a BOM breaks frontmatter parsing on some platforms,
# and PowerShell 5.1's default encodings would corrupt the Chinese fields.
function Set-StagedVersion {
    param([string]$File, [string]$Ver)
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    $text = [System.IO.File]::ReadAllText($File, [System.Text.Encoding]::UTF8)
    $new = [regex]::Replace($text, '(?m)^version:.*$', ('version: ' + $Ver), 1)
    if ($new -eq $text) { throw "no 'version:' line found in $File" }
    [System.IO.File]::WriteAllText($File, $new, $utf8)
}

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$root = Join-Path $env:TEMP ('wbskill_' + [guid]::NewGuid().ToString('N'))
try {
    # Layout A: SKILL.md at archive root
    $stageA = Join-Path $root 'a'
    New-Stage -Path $stageA
    if ($Version) { Set-StagedVersion -File (Join-Path $stageA 'SKILL.md') -Ver $Version; Write-Output "VERSION stamped $Version" }
    $zipA = Join-Path $OutDir ($Name + '.zip')
    if (Test-Path -LiteralPath $zipA) { Remove-Item -LiteralPath $zipA -Force }
    [System.IO.Compression.ZipFile]::CreateFromDirectory($stageA, $zipA)

    # Layout B: one wrapper folder containing SKILL.md
    $stageB = Join-Path $root 'b'
    New-Item -ItemType Directory -Path $stageB -Force | Out-Null
    $stageBInner = Join-Path $stageB $Name
    New-Stage -Path $stageBInner
    if ($Version) { Set-StagedVersion -File (Join-Path $stageBInner 'SKILL.md') -Ver $Version }
    $zipB = Join-Path $OutDir ($Name + '-folder.zip')
    if (Test-Path -LiteralPath $zipB) { Remove-Item -LiteralPath $zipB -Force }
    [System.IO.Compression.ZipFile]::CreateFromDirectory($stageB, $zipB)

    $rows = foreach ($z in @($zipA, $zipB)) {
        $info = Get-Item -LiteralPath $z
        [pscustomobject]@{
            Package = $info.Name
            MB      = [math]::Round($info.Length / 1MB, 3)
            Entries = ([System.IO.Compression.ZipFile]::OpenRead($z)).Entries.Count
        }
    }
    $rows | Format-Table -AutoSize | Out-String -Width 120 | Write-Output

    Write-Output '--- layout A entries (first 40) ---'
    $za = [System.IO.Compression.ZipFile]::OpenRead($zipA)
    $za.Entries | Select-Object -First 40 -ExpandProperty FullName | Write-Output
    Write-Output ('TOTAL_ENTRIES=' + $za.Entries.Count)
    $za.Dispose()

    # Guardrails: size limit, no stray bytecode, no hardcoded-looking API keys
    foreach ($z in @($zipA, $zipB)) {
        $mb = (Get-Item -LiteralPath $z).Length / 1MB
        if ($mb -gt $MaxMB) { Write-Output "WARN over-limit: $z = $([math]::Round($mb,3)) MB" }
    }
    $entryNames = @()
    $za = [System.IO.Compression.ZipFile]::OpenRead($zipA)
    foreach ($e in $za.Entries) { $entryNames += $e.FullName }
    $za.Dispose()
    $bad = $entryNames | Where-Object { $_ -match '__pycache__|\.pyc$|(^|/)\.env|\.log$' }
    if ($bad) { Write-Output ('WARN excluded-pattern-entries: ' + ($bad -join ', ')) } else { Write-Output 'CLEAN=no-cache-env-log-entries' }

    $hits = Get-ChildItem -LiteralPath $stageA -Recurse -File |
        Select-String -Pattern 'sk-[A-Za-z0-9]{20,}' -ErrorAction SilentlyContinue
    if ($hits) { Write-Output ('WARN possible-key: ' + (($hits | ForEach-Object { $_.Path }) -join ', ')) } else { Write-Output 'CLEAN=no-key-like-literals' }

    # Frontmatter the platform parses (SkillHub requires the market fields too)
    $md = [System.IO.File]::ReadAllText((Join-Path $stageA 'SKILL.md'), [System.Text.Encoding]::UTF8)
    $lines = ($md -split "`r?`n")
    $required = @('name', 'description', 'version', 'display_name', 'display_name_en', 'description_zh', 'description_en')
    foreach ($key in $required) {
        if ($lines -match ('^' + [regex]::Escape($key) + ':')) { Write-Output ('FRONTMATTER ok ' + $key) }
        else { Write-Output ('WARN frontmatter missing ' + $key) }
    }
    $verLine = ($lines | Where-Object { $_ -match '^version:' } | Select-Object -First 1)
    Write-Output ('PACKAGE_VERSION=' + ($verLine -replace '^version:\s*', '').Trim() + ' (must exceed the version already published)')
    $dnLine = ($lines | Where-Object { $_ -match '^display_name:' } | Select-Object -First 1)
    if ($dnLine) { Write-Output ('MARKET_NAME=' + ($dnLine -replace '^display_name:\s*', '').Trim() + ' (shown on the skill card)') }
    if (-not $Version) { Write-Output 'NOTE version taken from SKILL.md; pass -Version x.y.z to stamp a bump' }
    $totalKB = [math]::Round(((Get-ChildItem -LiteralPath $stageA -Recurse -File | Measure-Object -Sum Length).Sum / 1KB), 1)
    Write-Output "UNCOMPRESSED_KB=$totalKB FILES=$(($entryNames).Count)"

    Write-Output ('DONE ' + $zipA)
    Write-Output ('DONE ' + $zipB)
}
finally {
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction SilentlyContinue }
}
