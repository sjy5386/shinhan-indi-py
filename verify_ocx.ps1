# Verify INDI OCX registration. No admin required.
# Run: powershell -ExecutionPolicy Bypass -File verify_ocx.ps1

$progid64 = 'GIEXPERTCONTROL6.GIExpertControl6Ctrl.1'
$progid32 = 'GIEXPERTCONTROL.GiExpertControlCtrl.1'

Write-Host "=== INDI OCX registration check ===" -ForegroundColor Cyan

function Show-Progid($name){
    $p = "HKLM:\SOFTWARE\Classes\$name"
    if(-not (Test-Path $p)){
        Write-Host "  ProgID '$name' : MISSING" -ForegroundColor Red
        return
    }
    $clsid = (Get-ItemProperty "$p\CLSID" -ErrorAction SilentlyContinue).'(default)'
    if(-not $clsid){
        Write-Host "  ProgID '$name' : key exists, CLSID missing" -ForegroundColor Yellow
        return
    }
    Write-Host "  ProgID '$name'" -ForegroundColor Green
    Write-Host "    CLSID: $clsid"
    $is64 = Test-Path "HKLM:\SOFTWARE\Classes\CLSID\$clsid"
    $is32 = Test-Path "HKLM:\SOFTWARE\Classes\Wow6432Node\CLSID\$clsid"
    if($is64){
        $f = (Get-ItemProperty "HKLM:\SOFTWARE\Classes\CLSID\$clsid\InprocServer32" -ErrorAction SilentlyContinue).'(default)'
        Write-Host "    64bit hive: REGISTERED -> $f" -ForegroundColor Green
    } else { Write-Host "    64bit hive: not registered" -ForegroundColor Yellow }
    if($is32){
        $f = (Get-ItemProperty "HKLM:\SOFTWARE\Classes\Wow6432Node\CLSID\$clsid\InprocServer32" -ErrorAction SilentlyContinue).'(default)'
        Write-Host "    32bit hive: REGISTERED -> $f" -ForegroundColor Green
    } else { Write-Host "    32bit hive: not registered" -ForegroundColor Yellow }
}

Write-Host "`n[64bit ProgID - created by regsvr32 of giexpertcontrol64.ocx]"
Show-Progid $progid64

Write-Host "`n[32bit ProgID - auto registered by INDI HTS install]"
Show-Progid $progid32

Write-Host "`n=== Result ==="
$ok64 = Test-Path "HKLM:\SOFTWARE\Classes\$progid64"
$ok32 = Test-Path "HKLM:\SOFTWARE\Classes\$progid32"
if($ok64){
    Write-Host "64bit OK - put INDI_PROGID=$progid64 in .env" -ForegroundColor Green
} elseif($ok32){
    Write-Host "32bit fallback ready - put INDI_PROGID=$progid32 in .env (need 32bit Python)" -ForegroundColor Yellow
} else {
    Write-Host "Neither registered. Check INDI HTS install." -ForegroundColor Red
}
