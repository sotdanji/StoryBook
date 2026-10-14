@echo off
chcp 65001 > nul
title StoryBook 폴더명 변경 도구

echo ========================================================
echo   StoryBook Studio 폴더명 변경 도구
echo   [d:\AG\StroyBook] -> [d:\AG\StoryBook]
echo ========================================================
echo.

echo 1. 실행 중인 StoryBook 웹 서버(포트 8000)를 확인하고 종료합니다...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo    - 웹 서버 PID %%a 종료 중...
    taskkill /F /PID %%a > nul 2>&1
)
timeout /t 2 /nobreak > nul

echo.
echo 2. 폴더명 변경을 진행합니다...
cd /d "d:\AG"

if exist "d:\AG\StoryBook" (
    echo [알림] 이미 'd:\AG\StoryBook' 폴더가 존재합니다.
    goto END
)

rename "StroyBook" "StoryBook"

if exist "d:\AG\StoryBook" (
    echo.
    echo ========================================================
    echo   [성공] 'd:\AG\StoryBook' 으로 폴더명이 성공적으로 변경되었습니다!
    echo ========================================================
    echo.
    echo 이제 Antigravity IDE에서 새 폴더 [d:\AG\StoryBook]을 열어주세요.
) else (
    echo.
    echo [주의] Antigravity IDE나 VS Code가 현재 폴더를 열고 있어 변경이 지연되었습니다.
    echo IDE를 닫으신 후 이 창에서 엔터를 누르거나 탐색기에서 이름을 직접 변경해 주세요.
)

:END
echo.
pause
