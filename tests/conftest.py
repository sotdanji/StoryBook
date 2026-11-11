import sys
import os

# 테스트 중 외부 네트워크(Turso) 연결 방지 및 완전 격리된 로컬 SQLite 테스트 보장
os.environ["TURSO_DATABASE_URL"] = ""
os.environ["TURSO_AUTH_TOKEN"] = ""

# 프로젝트 루트 디렉터리를 sys.path에 추가하여 core, web 모듈을 원활히 import 가능하도록 설정
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

