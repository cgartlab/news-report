# edge-cdp.ps1 — launch Edge (or Chrome) with a local proxy and a CDP debug port
# for news-report module 06 (X-Browser). See SKILL.md「模块 06」.
#
# Usage (Windows PowerShell):
#   powershell -File bin/edge-cdp.ps1                # defaults: proxy 127.0.0.1:7897, port 9222
#   powershell -File bin/edge-cdp.ps1 -Proxy http://127.0.0.1:7890
#   powershell -File bin/edge-cdp.ps1 -Port 9223
#   powershell -File bin/edge-cdp.ps1 -Stop          # stop the CDP instance on this port
param(
  [string]$Proxy = 'http://127.0.0.1:7897',
  [int]$Port = 9222,
  [string]$UserDataDir = "$env:LOCALAPPDATA\edge-cdp-profile",
  [string]$StartUrl = 'https://x.com',
  [switch]$Stop
)

$edgeCandidates = @(
  'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
  'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
)
$edge = $edgeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edge) { Write-Error 'msedge.exe not found'; exit 1 }

if ($Stop) {
  $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force
    Write-Output "stopped CDP instance on port $Port"
  } else {
    Write-Output "nothing listening on port $Port"
  }
  exit 0
}

$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
  Write-Output "already listening on $Port (PID $($existing.OwningProcess)) — no-op"
  exit 0
}

if (-not (Test-Path $UserDataDir)) { New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null }

$args = @(
  "--remote-debugging-port=$Port",
  "--user-data-dir=$UserDataDir",
  "--proxy-server=$Proxy",
  '--no-first-run',
  '--no-default-browser-check'
)
if ($StartUrl) { $args += $StartUrl }

Start-Process -FilePath $edge -ArgumentList $args
Start-Sleep -Seconds 3

try {
  $v = (Invoke-WebRequest -Uri "http://127.0.0.1:$Port/json/version" -UseBasicParsing -TimeoutSec 5).Content
  $browser = ($v | ConvertFrom-Json).Browser
  Write-Output "OK: $browser  CDP = http://127.0.0.1:$Port"
} catch {
  Write-Error "Edge launched but CDP port $Port did not answer: $($_.Exception.Message)"
  exit 1
}
