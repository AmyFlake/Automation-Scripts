<# 
.SYNOPSIS
  Export Windows Event Logs to CSV and EVTX with time filters.
#>
[CmdletBinding()]
param(
  [string[]]$LogName = @('System','Application'),
  [int]$Hours = 24,
  [string]$Since,
  [string]$OutDir = ".\out"
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$ts = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$sessionDir = Join-Path $OutDir "winevents_${ts}"
New-Item -ItemType Directory -Force -Path $sessionDir | Out-Null
if ($Since) { $start = [DateTime]::Parse($Since) } else { $start = (Get-Date).AddHours(-1 * $Hours) }
foreach ($log in $LogName) {
  $csv = Join-Path $sessionDir ("{0}.csv" -f ($log -replace '[\\/]','_'))
  $evtx = Join-Path $sessionDir ("{0}.evtx" -f ($log -replace '[\\/]','_'))
  $events = Get-WinEvent -FilterHashtable @{ LogName = $log; StartTime = $start } -ErrorAction SilentlyContinue
  $events | Select-Object TimeCreated, Id, LevelDisplayName, ProviderName, LogName, MachineName, Message | `
           Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
  try { wevtutil epl "$log" "$evtx" /q:"*[System[TimeCreated[@SystemTime>='$(Get-Date $start -Format o)']]]" } catch { Write-Warning "wevtutil export failed for $log: $_" }
}
Write-Host "Export complete: $sessionDir"
