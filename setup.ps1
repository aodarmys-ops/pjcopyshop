# PJ Copy Shop - POS Automated Setup Script
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
Set-Location $scriptDir

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "       🛠️  ระบบติดตั้งโปรแกรมขายหน้าร้าน PJ Copy Shop POS" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "โฟลเดอร์โปรแกรม: $scriptDir`n" -ForegroundColor Gray

# ฟังก์ชันตรวจสอบว่า Python รันได้จริงหรือไม่ (ไม่ใช่ shortcut เปล่าของ Windows Store)
function Test-PythonExecutable($path) {
    try {
        $out = & $path -c "import sys; print(sys.version_info[0])" 2>$null
        if ($out -and $out.Trim() -eq "3") {
            return $true
        }
    } catch {}
    return $false
}

$pythonExe = $null
$pythonCmd = $null

# 1. ตรวจสอบว่าใน venv เดิมมี Python ใช้งานได้อยู่แล้วหรือไม่
$existingVenvPy = Join-Path $scriptDir "venv\Scripts\python.exe"
if (Test-Path $existingVenvPy) {
    if (Test-PythonExecutable $existingVenvPy) {
        $pythonExe = $existingVenvPy
        Write-Host "✅ ตรวจพบ Virtual Environment เดิมที่พร้อมใช้งาน" -ForegroundColor Green
    }
}

# 2. หากยังไม่มี venv หรือ venv เดิมใช้ไม่ได้ ให้ค้นหา Python ในเครื่อง
if (-not $pythonExe) {
    Write-Host "[1/4] ตรวจสอบสภาพแวดล้อม Python ในเครื่อง..." -ForegroundColor Yellow

    # ตรวจคำสั่ง python ทั่วไป
    if (Test-PythonExecutable "python") {
        $pythonCmd = "python"
    }
    # ตรวจคำสั่ง py -3
    elseif (Test-PythonExecutable "py") {
        $pythonCmd = "py"
    }
    else {
        # ค้นหาในโฟลเดอร์ติดตั้งมาตรฐาน
        $candidatePaths = @(
            "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
            "C:\Program Files\Python314\python.exe",
            "C:\Program Files\Python313\python.exe",
            "C:\Program Files\Python312\python.exe",
            "C:\Program Files\Python311\python.exe",
            "C:\Program Files\Python310\python.exe",
            "C:\Python311\python.exe",
            "C:\Python310\python.exe"
        )
        foreach ($c in $candidatePaths) {
            if (Test-Path $c) {
                if (Test-PythonExecutable $c) {
                    $pythonCmd = $c
                    break
                }
            }
        }
    }

    # 3. หากไม่พบ Python ในเครื่องเลย -> ดาวน์โหลดและติดตั้งอัตโนมัติ โดยไม่ต้องให้ผู้ใช้ไปหาติดตั้งเอง
    if (-not $pythonCmd) {
        Write-Host "`n========================================================================" -ForegroundColor Yellow
        Write-Host "⚠️  ไม่พบ Python บนเครื่องนี้" -ForegroundColor Yellow
        Write-Host "⚙️  กำลังดาวน์โหลดและติดตั้ง Python ให้อัตโนมัติ (กรุณารอสักครู่)..." -ForegroundColor Cyan
        Write-Host "    * ผู้ใช้ไม่ต้องไปค้นหาหรือติดตั้งเอง ระบบจะจัดการให้ทั้งหมด *" -ForegroundColor Gray
        Write-Host "========================================================================`n" -ForegroundColor Yellow

        # 3.1 ลองใช้ winget ก่อน
        $wingetInstalled = $false
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "  - กำลังติดตั้งผ่าน Windows Package Manager (winget)..." -ForegroundColor Gray
            try {
                & winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements --silent 2>$null | Out-Null
            } catch {}
        }

        $installedPy = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
        if (Test-Path $installedPy) {
            if (Test-PythonExecutable $installedPy) {
                $pythonCmd = $installedPy
                $wingetInstalled = $true
            }
        }

        # 3.2 หาก winget ไม่สำเร็จ ให้ดาวน์โหลดตัวติดตั้งทางการจาก python.org
        if (-not $wingetInstalled) {
            Write-Host "  - กำลังดาวน์โหลดไฟล์ติดตั้ง Python 3.11 จาก python.org..." -ForegroundColor Gray
            $installerPath = Join-Path $env:TEMP "python-3.11.9-amd64.exe"
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $installerPath -UseBasicParsing
                
                Write-Host "  - กำลังติดตั้ง Python 3.11 แบบอัตโนมัติ (Silent Install)..." -ForegroundColor Gray
                $proc = Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 Shortcuts=0" -Wait -PassThru
                Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
            } catch {
                Write-Host "  ⚠️ การดาวน์โหลดหรือติดตั้งตัวมาตรฐานมีข้อจำกัด: $_" -ForegroundColor Yellow
            }

            if (Test-Path $installedPy) {
                if (Test-PythonExecutable $installedPy) {
                    $pythonCmd = $installedPy
                }
            }
        }

        # 3.3 สำรองกรณีเครื่องติดสิทธิ์ Admin: Portable Embedded Python
        if (-not $pythonCmd) {
            Write-Host "  - กำลังติดตั้ง Portable Python Runtime สำรอง (ไม่ต้องสิทธิ์ Admin)..." -ForegroundColor Gray
            $runtimeDir = Join-Path $scriptDir "python_runtime"
            try {
                [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
                $zipPath = Join-Path $env:TEMP "py_embed.zip"
                Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip" -OutFile $zipPath -UseBasicParsing
                Expand-Archive -Path $zipPath -DestinationPath $runtimeDir -Force
                Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

                # เปิดใช้งาน import site ใน python311._pth
                $pth = Join-Path $runtimeDir "python311._pth"
                if (Test-Path $pth) {
                    (Get-Content $pth) | ForEach-Object { if ($_ -match '#import site') { 'import site' } else { $_ } } | Set-Content $pth -Encoding utf8
                }

                # ดาวน์โหลด get-pip.py
                $pipPy = Join-Path $runtimeDir "get-pip.py"
                Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $pipPy -UseBasicParsing
                Start-Process -FilePath (Join-Path $runtimeDir "python.exe") -ArgumentList "$pipPy --no-warn-script-location" -Wait
                Remove-Item $pipPy -Force -ErrorAction SilentlyContinue

                $embeddedPy = Join-Path $runtimeDir "python.exe"
                if (Test-PythonExecutable $embeddedPy) {
                    $pythonExe = $embeddedPy
                    Write-Host "✅ ติดตั้ง Portable Python Runtime สำเร็จ!" -ForegroundColor Green
                }
            } catch {
                Write-Host "❌ ติดตั้ง Portable Runtime ไม่สำเร็จ: $_" -ForegroundColor Red
            }
        }

        if (-not $pythonCmd -and -not $pythonExe) {
            Write-Host "`n❌ ไม่สามารถติดตั้ง Python ได้โดยอัตโนมัติ กรุณาตรวจสอบการเชื่อมต่ออินเทอร์เน็ต" -ForegroundColor Red
            Read-Host "กด Enter เพื่อออก..."
            exit 1
        }
    }

    # 4. สร้าง Virtual Environment (venv) หากไม่ได้ใช้ embedded runtime
    if (-not $pythonExe) {
        $pyVersion = & $pythonCmd --version 2>&1
        Write-Host "✅ ตรวจพบ Python: $pyVersion" -ForegroundColor Green

        $venvDir = Join-Path $scriptDir "venv"
        Write-Host "  - กำลังสร้าง Virtual Environment (venv)..." -ForegroundColor Gray
        try {
            & $pythonCmd -m venv $venvDir
            $pythonExe = Join-Path $venvDir "Scripts\python.exe"
        } catch {
            Write-Host "  ⚠️ สร้าง venv ไม่สำเร็จ จะใช้งานผ่าน Python หลักโดยตรง" -ForegroundColor Yellow
            $pythonExe = $pythonCmd
        }
    }
}

# 5. ติดตั้งและอัปเดต Library ที่จำเป็น
Write-Host "`n[2/4] กำลังติดตั้งไลบรารีที่จำเป็น (requirements.txt)..." -ForegroundColor Yellow
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $reqFile = Join-Path $scriptDir "requirements.txt"
    Write-Host "  - กำลังติดตั้งชุดไลบรารีสำหรับระบบ POS (กรุณารอสักครู่)..." -ForegroundColor Gray
    
    # ติดตั้งลงในสภาพแวดล้อมหลักที่เลือก
    & $pythonExe -m pip install --upgrade pip --quiet 2>$null
    & $pythonExe -m pip install --prefer-binary -r $reqFile
    
    # หากมี Python หลักของเครื่อง ให้ติดตั้งเผื่อไว้ด้วย
    if ($pythonCmd -and $pythonCmd -ne $pythonExe) {
        & $pythonCmd -m pip install --prefer-binary -r $reqFile --quiet 2>$null
    }
    
    # ตรวจสอบการ import โมดูลสำคัญ
    $testImport = & $pythonExe -c "import flask, waitress, qrcode, requests, flask_limiter; print('OK')" 2>&1
    if ($testImport -match 'OK') {
        Write-Host "✅ ไลบรารีทั้งหมดพร้อมใช้งาน (Flask, Waitress, QRCode, Requests, Limiter ฯลฯ)" -ForegroundColor Green
    } else {
        Write-Host "⚠️ ตรวจพบข้อผิดพลาดขณะโหลดไลบรารี: $testImport" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ มีข้อผิดพลาดระหว่างติดตั้งไลบรารี: $_" -ForegroundColor Yellow
} finally {
    $ErrorActionPreference = $oldEap
}

# 6. เตรียมฐานข้อมูล SQLite และสร้างบัญชีเริ่มต้น
Write-Host "`n[3/4] ตรวจสอบและตั้งค่าฐานข้อมูล (Database)..." -ForegroundColor Yellow

# ปิด Process Python เดิมที่อาจล็อกไฟล์ xerox.db อยู่
try {
    $runningPy = Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'run_server|app\.py' }
    if ($runningPy) {
        Write-Host "  ⚠️ ตรวจพบระบบ POS กำลังรันค้างอยู่ กำลังปิดเพื่ออัปเดตฐานข้อมูล..." -ForegroundColor Gray
        $runningPy | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Milliseconds 600
    }
} catch {}

try {
    $dbInitScript = @"
import sys, os
script_dir = r'$scriptDir'
sys.path.insert(0, script_dir)
os.chdir(script_dir)
try:
    from app import init_db, migrate_pins_to_hash, DB_FILE
    init_db()
    migrate_pins_to_hash()
    db_path = DB_FILE if os.path.isabs(DB_FILE) else os.path.join(script_dir, DB_FILE)
    if os.path.exists(db_path):
        print('DB_READY')
except Exception as ex:
    import traceback
    traceback.print_exc()
"@
    # ปรับ ErrorAction ชั่วคราวไม่ให้ PowerShell แตกตื่นกับ stderr ของ Python
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $dbRes = & $pythonExe -c $dbInitScript 2>&1
    $ErrorActionPreference = $oldEap

    $outputStr = ($dbRes | Out-String).Trim()
    if ($outputStr -match 'DB_READY') {
        Write-Host "✅ ฐานข้อมูล SQLite พร้อมใช้งานเรียบร้อย" -ForegroundColor Green
    } else {
        Write-Host "❌ เกิดข้อผิดพลาดกับฐานข้อมูล:" -ForegroundColor Red
        if ($outputStr -match 'database is locked') {
            Write-Host "  ⚠️  สาเหตุ: ไฟล์ฐานข้อมูล xerox.db กำลังถูกโปรแกรมอื่นล็อกอยู่" -ForegroundColor Yellow
            Write-Host "  👉 วิธีแก้: ให้ปิดหน้าจอ POS หรือปิดโปรแกรม Python ใน Task Manager แล้วลองรัน SETUP.bat ใหม่อีกครั้ง" -ForegroundColor Cyan
        } elseif ($outputStr -match 'No module named') {
            Write-Host "  ⚠️  สาเหตุ: ไลบรารี Python ยังติดตั้งไม่ครบถ้วน" -ForegroundColor Yellow
            Write-Host "  👉 รายละเอียด: $outputStr" -ForegroundColor Gray
            Write-Host "  👉 วิธีแก้: กรุณาเชื่อมต่ออินเทอร์เน็ต แล้วรันคำสั่งติดตั้งไลบรารีซ้ำ" -ForegroundColor Cyan
        } else {
            Write-Host "  $outputStr" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "❌ เกิดข้อผิดพลาดกับฐานข้อมูล: $_" -ForegroundColor Red
}

# 7. สร้างปุ่มลัด (Shortcut) บน Desktop และอนุญาต Firewall
Write-Host "`n[4/4] สร้างปุ่มลัดบนหน้าจอ Desktop และตั้งค่าระบบ..." -ForegroundColor Yellow
try {
    $ws = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shortcutPath = Join-Path $desktop "PJ Copy Shop POS.lnk"
    $shortcut = $ws.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = Join-Path $scriptDir "2_Start_POS.bat"
    $shortcut.WorkingDirectory = $scriptDir
    $shortcut.Description = "เปิดระบบขายหน้าร้าน PJ Copy Shop POS"
    $shortcut.IconLocation = "shell32.dll,220"
    $shortcut.Save()
    Write-Host "✅ สร้างปุ่มลัด 'PJ Copy Shop POS' บนหน้าจอ Desktop เรียบร้อย" -ForegroundColor Green
} catch {
    Write-Host "⚠️ ไม่สามารถสร้างปุ่มลัดบน Desktop ได้: $_" -ForegroundColor Yellow
}

# ตั้งค่า Firewall พอร์ต 5000 สำหรับเครือข่ายภายในร้าน
try {
    netsh advfirewall firewall add rule name="PJ Copy Shop POS (Port 5000)" dir=in action=allow protocol=TCP localport=5000 2>$null | Out-Null
    Write-Host "✅ ตั้งค่า Windows Firewall พอร์ต 5000 เรียบร้อย" -ForegroundColor Green
} catch {}

# หา IP Address ภายในเครือข่าย Wi-Fi/LAN
$localIp = "127.0.0.1"
try {
    $ipOut = & $pythonExe -c "import socket; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print(s.getsockname()[0]); s.close()" 2>$null
    if ($ipOut) {
        $localIp = $ipOut.Trim()
    }
} catch {}

# สรุปผลการติดตั้ง
Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host "        🎉  ติดตั้งระบบ PJ Copy Shop POS เสร็จสมบูรณ์พร้อมใช้งาน!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "`n  🖥️  วิธีเปิดใช้งาน:" -ForegroundColor White
Write-Host "      1. ดับเบิลคลิกไอคอน " -NoNewline -ForegroundColor White
Write-Host "'PJ Copy Shop POS'" -NoNewline -ForegroundColor Yellow
Write-Host " บนหน้าจอ Desktop" -ForegroundColor White
Write-Host "      หรือ ดับเบิลคลิกไฟล์ " -NoNewline -ForegroundColor White
Write-Host "'2_Start_POS.bat'" -NoNewline -ForegroundColor Yellow
Write-Host " ในโฟลเดอร์นี้`n" -ForegroundColor White

Write-Host "  🌐 ช่องทางเข้าใช้งานระบบ:" -ForegroundColor White
Write-Host "      - เครื่องนี้ (Local):           " -NoNewline -ForegroundColor White
Write-Host "http://localhost:5000" -ForegroundColor Cyan
if ($localIp -ne "127.0.0.1") {
    Write-Host "      - มือถือ/เครื่องอื่นในวง Wi-Fi: " -NoNewline -ForegroundColor White
    Write-Host "http://$($localIp):5000" -ForegroundColor Cyan
}

Write-Host "`n  🔑 ข้อมูลเข้าสู่ระบบเริ่มต้น:" -ForegroundColor White
Write-Host "      - ผู้ใช้งาน (User): " -NoNewline -ForegroundColor White
Write-Host "Admin" -ForegroundColor Yellow
Write-Host "      - รหัส PIN:        " -NoNewline -ForegroundColor White
Write-Host "1234" -ForegroundColor Yellow
Write-Host "========================================================================`n" -ForegroundColor Cyan

# ถามผู้ใช้ว่าต้องการเปิดโปรแกรมเลยหรือไม่
$answer = Read-Host "ต้องการเปิดใช้งานระบบ POS ตอนนี้เลยหรือไม่? (กด Y เพื่อเปิด / กด N เพื่อออก)"
if ($answer -eq 'Y' -or $answer -eq 'y') {
    Start-Process (Join-Path $scriptDir "2_Start_POS.bat")
}
