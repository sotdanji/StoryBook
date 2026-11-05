@echo off
chcp 65001 > nul
cd /d "%~dp0"
title StoryBook Studio - 시집만들기

echo ====================================================================
echo   📖 StoryBook Studio - 나만의 기억 시화집 만들기
echo   "가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다."
echo ====================================================================
echo.
echo   잠시 후 웹 브라우저가 열리며 집필실 화면이 나타납니다...
echo   (종료하시려면 이 창을 닫으시면 됩니다)
echo.

:: 바탕화면에 '시화집 창작' 바로가기가 없으면 자동으로 생성 (최초 1회 자동 생성)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desk = $ws.SpecialFolders('Desktop'); $lnk = Join-Path $desk '시화집 창작.lnk'; if (-not (Test-Path $lnk)) { $sc = $ws.CreateShortcut($lnk); $sc.TargetPath = '%~dp0실행하기.bat'; $sc.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0web\static\favicon.ico') { $sc.IconLocation = '%~dp0web\static\favicon.ico,0' } else { $sc.IconLocation = 'shell32.dll,130' }; $sc.Description = 'StoryBook Studio - 기억 기반 감성 시화집 창작소'; $sc.Save(); Write-Host '  [안내] 바탕화면에 [시화집 창작] 바로가기 아이콘을 생성하였습니다.' }" 2>nul

if exist "%~dp0_internal\python.exe" (
    "%~dp0_internal\python.exe" run_web.py
    goto end
)

if exist "%~dp0python\python.exe" (
    "%~dp0python\python.exe" run_web.py
    goto end
)

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" run_web.py
    goto end
)

if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" run_web.py
    goto end
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    python run_web.py
    goto end
)

echo ⚠️ 파이썬 실행 환경을 찾을 수 없습니다.
echo    폴더 압축이 정상적으로 풀렸는지 확인해 주세요.

:end
pause
