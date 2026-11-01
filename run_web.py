import sys
import os
import socket
import threading
import webbrowser
import uvicorn

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """해당 포트가 이미 사용 중인지 확인합니다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """사용 가능한 포트를 찾습니다."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port):
            return port
    return start_port

def open_browser(port: int):
    """서버가 시작된 후 기본 브라우저를 자동으로 엽니다."""
    url = f"http://localhost:{port}"
    print(f"\n✨ StoryBook Studio 웹페이지를 브라우저에서 엽니다: {url}")
    webbrowser.open(url)

def main():
    target_port = find_available_port(8000)

    print("=" * 65)
    print("📖 StoryBook Studio 웹 애플리케이션 시작")
    print("“가장 개인적인 기억이 가장 깊은 문학이자 예술이 된다.”")
    print(f"브라우저 주소: http://localhost:{target_port}")
    print("종료하려면 터미널에서 Ctrl+C를 누르세요.")
    print("=" * 65)

    # 1.2초 뒤 브라우저 자동 오픈
    threading.Timer(1.2, open_browser, args=[target_port]).start()

    # 소스 실행 시 코드 변경 자동 반영 (PyInstaller 패키징 환경 제외)
    is_frozen = getattr(sys, 'frozen', False)
    use_reload = not is_frozen and ("--no-reload" not in sys.argv)
    uvicorn.run("web.app:app", host="127.0.0.1", port=target_port, reload=use_reload, log_level="info")

if __name__ == "__main__":
    main()
