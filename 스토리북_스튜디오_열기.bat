@echo off
chcp 65001 > nul
cd /d "%~dp0"
title StoryBook Studio - 기억 기반 시화집 독립출판 스튜디오

echo ====================================================================
echo   📖 StoryBook Studio 웹 스튜디오를 실행합니다.
echo   “가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다.”
echo ====================================================================
echo.

set PYTHON_BIN=""

if exist "_internal\python.exe" (
    echo [런타임] 내장 포터블 엔진(_internal)을 사용합니다...
    set PYTHON_BIN="_internal\python.exe"
) else if exist "python\python.exe" (
    echo [런타임] 내장 임베디드 파이썬(python)을 사용합니다...
    set PYTHON_BIN="python\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    echo [런타임] 가상환경(.venv) 파이썬을 사용합니다...
    set PYTHON_BIN=".venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %errorlevel% equ 0 (
        echo [런타임] 시스템 파이썬을 사용합니다...
        set PYTHON_BIN=python
    )
)

if %PYTHON_BIN%=="" (
    echo ⚠️ 파이썬 실행 환경을 찾을 수 없습니다.
    echo    스토리북 스튜디오 폴더 내에 정상적인 파이썬 환경이 있는지 확인해 주세요.
    pause
    exit /b 1
)

%PYTHON_BIN% run_web.py

if %errorlevel% neq 0 (
    echo.
    echo ⚠️ 스튜디오 실행 중 오류가 발생했습니다.
    pause
)
