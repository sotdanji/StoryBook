@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion
title StoryBook Studio - 시화집 독립출판 스튜디오

echo ====================================================================
echo   StoryBook Studio (기억 기반 시화집 독립출판 웹 스튜디오)
echo   - 100%% 무료 / API 키 불필요
echo   - 300 DPI 출판용 인쇄 규격 및 Canva 완벽 호환
echo ====================================================================
echo.

cd /d "%~dp0"

:: 1. 가상환경(.venv)이 이미 설치되어 있는지 확인
if exist ".venv\Scripts\python.exe" (
    echo [1/2] 등록된 실행 환경(.venv)을 확인했습니다.
    echo [2/2] 웹 스튜디오를 시작합니다... (잠시 후 브라우저가 자동으로 열립니다)
    echo.
    .venv\Scripts\python.exe run_web.py
    goto :end
)

:: 2. 가상환경이 없는 경우: 최초 자동 설치 파이프라인 가동
echo [안내] 최초 실행 환경이 감지되지 않아, 자동으로 설치를 진행합니다.
echo.

:: 2-1. 시스템에 Python 설치 여부 확인
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% neq 0 (
        echo ====================================================================
        echo [오류] PC에 Python(파이썬 3.10 이상)이 설치되어 있지 않습니다.
        echo.
        echo 파이썬 공식 사이트에서 파이썬을 설치해 주세요.
        echo (주의: 설치 시 반드시 "Add python.exe to PATH"에 체크해야 합니다!)
        echo.
        echo 브라우저로 파이썬 다운로드 페이지를 열어드립니다...
        echo ====================================================================
        start "" https://www.python.org/downloads/
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=py
    )
) else (
    set PYTHON_CMD=python
)

echo [1/3] 가상 실행 환경(.venv)을 생성하는 중입니다...
%PYTHON_CMD% -m venv .venv
if %errorlevel% neq 0 (
    echo [오류] 가상환경 생성에 실패했습니다. 파이썬 권한을 확인해주세요.
    pause
    exit /b 1
)

echo [2/3] 필수 출판 및 인공지능 패키지를 설치하는 중입니다...
echo (인터넷 속도에 따라 30초~1분 정도 소요될 수 있습니다)
.venv\Scripts\python.exe -m pip install --upgrade pip -q
.venv\Scripts\python.exe -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [오류] 필수 패키지 설치 중 오류가 발생했습니다.
    pause
    exit /b 1
)

echo.
echo ====================================================================
echo  🎉 설치가 성공적으로 완료되었습니다! 웹 스튜디오를 실행합니다.
echo ====================================================================
echo.

echo [3/3] 웹 스튜디오를 시작합니다... (잠시 후 브라우저가 자동으로 열립니다)
.venv\Scripts\python.exe run_web.py

:end
pause
