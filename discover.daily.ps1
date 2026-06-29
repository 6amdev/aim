# Aim discover — รันอัตโนมัติรายวัน (เรียกโดย Windows Task Scheduler)
# หา skill ใหม่เข้าคิว data/discovered.json (ไม่ merge — รอรีวิว)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo

$py = "$repo\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"   # กัน log ภาษาไทยเพี้ยนตอนรันใน Task Scheduler
if (-not $env:AIM_SECRETS_FILE) {
    $env:AIM_SECRETS_FILE = "G:\Projects_2027\home-lab\secrets\all-keys.env"
}

$log = "$repo\data\discover.log"
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"=== $stamp discover run ===" | Out-File -FilePath $log -Append -Encoding utf8

& $py -m aim discover --limit 10 2>&1 | Tee-Object -FilePath $log -Append
