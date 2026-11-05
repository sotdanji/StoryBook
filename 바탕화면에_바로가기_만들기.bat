@echo off
chcp 65001 > nul
cd /d "%~dp0"
title StoryBook Studio - 바탕화면 바로가기 생성

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desk = $ws.SpecialFolders('Desktop'); $lnk = Join-Path $desk '시화집 창작.lnk'; $sc = $ws.CreateShortcut($lnk); $sc.TargetPath = '%~dp0실행하기.bat'; $sc.WorkingDirectory = '%~dp0'; if (Test-Path '%~dp0web\static\favicon.ico') { $sc.IconLocation = '%~dp0web\static\favicon.ico,0' } else { $sc.IconLocation = 'shell32.dll,130' }; $sc.Description = 'StoryBook Studio - 기억 기반 감성 시화집 창작소'; $sc.Save(); Write-Host '===================================================================='; Write-Host '  [완료] 바탕화면에 [시화집 창작] 바로가기 아이콘이 생성되었습니다!'; Write-Host ('  위치: ' + $lnk); Write-Host '===================================================================='"

echo.
echo   이제 바탕화면의 [시화집 창작] 아이콘을 더블클릭하시면
echo   언제든 집필실이 바로 열립니다.
echo.
pause
