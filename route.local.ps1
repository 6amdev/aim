# Aim local runner — ค้น capability ในเครื่อง ไม่ต้องเปิด server
# usage: powershell -File route.local.ps1 -Task "<งาน>" [-TopK 5]
param(
    [Parameter(Mandatory = $true)][string]$Task,
    [int]$TopK = 5
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
# OpenRouter key สำหรับ --verify (อยู่ใน home-lab secrets)
if (-not $env:AIM_SECRETS_FILE) {
    $env:AIM_SECRETS_FILE = "G:\Projects_2027\home-lab\secrets\all-keys.env"
}
Set-Location $repo
& "$repo\.venv\Scripts\python.exe" -m aim route $Task --top-k $TopK --local --verify
