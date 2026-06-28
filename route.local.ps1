# Aim local runner — ค้น capability ในเครื่อง ไม่ต้องเปิด server
# ครั้งแรก: ตั้ง venv + ลง dep + สร้าง index ให้อัตโนมัติ (ไม่ต้องพิมพ์เอง)
# usage: powershell -File route.local.ps1 -Task "<งาน>" [-TopK 5] [-Json]
param(
    [Parameter(Mandatory = $true)][string]$Task,
    [int]$TopK = 5,
    [switch]$Json
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

$py = "$repo\.venv\Scripts\python.exe"

# --- bootstrap (ทำครั้งเดียว, ครั้งถัดไปข้าม) ---
if (-not (Test-Path $py)) {
    Write-Host "[aim] ตั้ง venv ครั้งแรก ..." -ForegroundColor Cyan
    python -m venv "$repo\.venv"
    & $py -m pip install --quiet --upgrade pip
    & $py -m pip install --quiet -r "$repo\requirements.txt"
}
if (-not (Test-Path "$repo\data\local_index.json")) {
    Write-Host "[aim] สร้าง local index ครั้งแรก (embed 192 capability) ..." -ForegroundColor Cyan
    & $py -m aim index --local
}

# OpenRouter key สำหรับ --verify (อยู่ใน home-lab secrets)
if (-not $env:AIM_SECRETS_FILE) {
    $env:AIM_SECRETS_FILE = "G:\Projects_2027\home-lab\secrets\all-keys.env"
}

# --- route ---
$cmd = @("-m", "aim", "route", $Task, "--top-k", $TopK, "--local", "--verify")
if ($Json) { $cmd += "--json" }
& $py @cmd
