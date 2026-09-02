<#
Mirror the irreplaceable local data -- maps/ and reference/ -- to two backup
locations on different drives. Both directories are gitignored and are the
project's only evidence; on 2026-09-01 a recursive delete followed a directory
junction and wiped them, and the bot's AGTST test maps were lost for good.

Usage (from the repo root):
    powershell -ExecutionPolicy Bypass -File tools\backup_corpus.ps1

Refuses to run if a reparse point (junction/symlink) exists inside either
source tree, because a mirror through a junction copies the wrong thing and a
mirror WITH /MIR would delete through it.  Never uses /MIR: files removed from
the source are kept in the backup (/E without /PURGE).
#>
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$sources = @("maps", "reference")
$targets = @("D:\Games\DOS\llmapper-corpus-backup", "C:\Users\jiriv\llmapper-corpus-backup")

foreach ($name in $sources) {
    $src = Join-Path $repo $name
    if (-not (Test-Path $src)) { Write-Output "missing source: $src"; continue }
    $links = Get-ChildItem $src -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
    if ($links) {
        Write-Output "REFUSING: reparse points inside $src :"
        $links | ForEach-Object { Write-Output "   $($_.FullName)" }
        exit 2
    }
    foreach ($root in $targets) {
        $dst = Join-Path $root $name
        New-Item -ItemType Directory -Force -Path $dst | Out-Null
        robocopy $src $dst /E /R:1 /W:1 /NFL /NDL /NJH /NP | Select-Object -Last 3
        $n = (Get-ChildItem $dst -Recurse -File | Measure-Object).Count
        Write-Output ("{0} -> {1}: {2} files" -f $name, $dst, $n)
    }
}
