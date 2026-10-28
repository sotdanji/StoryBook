@echo off
chcp 65001 > nul
cd /d "%~dp0"
title StoryBook Studio - 바탕화면 바로가기 생성

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desk = $ws.SpecialFolders('Desktop'); $lnk = Join-Path $desk '시집만들기.lnk'; $sc = $ws.CreateShortcut($lnk); $sc.TargetPath = '%~dp0시집만들기.bat'; $sc.WorkingDirectory = '%~dp0'; $sc.IconLocation = 'shell32.dll,130'; $sc.Description = 'StoryBook Studio - 기억 기반 나만의 시화집 만들기'; $sc.Save(); Write-Host '===================================================================='; Write-Host '  [완료] 바탕화면에 [시집만들기] 바로가기 아이콘이 생성되었습니다!'; Write-Host ('  위치: ' + $lnk); Write-Host '===================================================================='"

echo.
echo   이제 바탕화면의 [시집만들기] 아이콘을 더블클릭하시면
echo   언제든 집필실이 바로 열립니다.
echo.
pause
