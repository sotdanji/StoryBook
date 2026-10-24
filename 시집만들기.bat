@echo off
chcp 65001 > nul
cd /d "%~dp0"
title StoryBook Studio - 시집만들기

echo ====================================================================
echo   StoryBook Studio - 나만의 기억 시화집 만들기
echo   "가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다."
echo ====================================================================
echo.
echo   잠시 후 웹 브라우저가 열리며 집필실 화면이 나타납니다...
echo   (종료하시려면 이 창을 닫으시면 됩니다)
echo.

:: 바탕화면에 '시집만들기' 바로가기가 없으면 자동으로 생성
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\시집만들기.lnk"
if not exist "%SHORTCUT_PATH%" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath = '%~dp0시집만들기.bat'; $sc.WorkingDirectory = '%~dp0'; $sc.IconLocation = 'shell32.dll,130'; $sc.Description = 'StoryBook Studio - 기억 기반 나만의 시화집 만들기'; $sc.Save()" > nul 2>&1
    echo   [안내] 바탕화면에 '시집만들기' 바로가기 아이콘을 생성하였습니다.
    echo.
)

if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" run_web.py
    goto end
)

if exist "%~dp0_internal\python.exe" (
    "%~dp0_internal\python.exe" run_web.py
    goto end
)

python run_web.py

:end
pause
