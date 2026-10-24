@echo off
chcp 65001 > nul
cd /d "%~dp0"
title StoryBook Studio - 바탕화면 바로가기 생성

set "SHORTCUT_PATH=%USERPROFILE%\Desktop\시집만들기.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut('%SHORTCUT_PATH%'); $sc.TargetPath = '%~dp0시집만들기.bat'; $sc.WorkingDirectory = '%~dp0'; $sc.IconLocation = 'shell32.dll,130'; $sc.Description = 'StoryBook Studio - 기억 기반 나만의 시화집 만들기'; $sc.Save()" > nul 2>&1

echo ====================================================================
echo   [완료] 바탕화면에 [시집만들기] 바로가기 아이콘이 생성되었습니다!
echo   위치: %SHORTCUT_PATH%
echo ====================================================================
echo.
echo   이제 바탕화면의 [시집만들기] 아이콘을 더블클릭하시면
echo   언제든 집필실이 바로 열립니다.
echo.
pause
