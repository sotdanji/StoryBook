import sys
import os

# 프로젝트 루트 디렉터리를 sys.path에 추가하여 core, web 모듈을 원활히 import 가능하도록 설정
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
