import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:8000"

# 1. GET /api/book_spec 조사
print("=== 1. book_spec ===")
try:
    req = urllib.request.urlopen(f"{BASE_URL}/api/book_spec")
    data = json.loads(req.read().decode("utf-8"))
    print("book_spec keys:", list(data.keys()))
    print("book_spec data:", data)
except Exception as e:
    print("book_spec err:", e)

# 2. Thesaurus lookup URL 인코딩 조사
print("\n=== 2. Thesaurus lookup with quote ===")
try:
    word = urllib.parse.quote("어머니")
    req = urllib.request.urlopen(f"{BASE_URL}/api/thesaurus/lookup?word={word}")
    data = json.loads(req.read().decode("utf-8"))
    print("Thesaurus lookup:", data.get("found"), data.get("alternatives", [])[:3])
except Exception as e:
    print("Thesaurus lookup err:", e)

# 3. Revisions URL 인코딩 조사
print("\n=== 3. Revisions with quote ===")
try:
    ep = urllib.parse.quote("제01화")
    req = urllib.request.urlopen(f"{BASE_URL}/api/revisions/{ep}")
    data = json.loads(req.read().decode("utf-8"))
    print("Revisions count:", len(data.get("revisions", [])))
except Exception as e:
    print("Revisions err:", e)

# 4. generate_lyrics 응답 조사
print("\n=== 4. generate_lyrics ===")
try:
    body = json.dumps({
        "episode_no": "제01화",
        "title": "테스트 시",
        "poem_body": "골목길 돌아설 때\n저녁노을이 붉게 물들었네\n그리운 이름 하나\n바람 속에 흩어지네"
    }).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/api/generate_lyrics", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("lyrics response keys:", list(data.keys()))
        print("lyrics snippet:", data.get("lyrics", "")[:120])
except Exception as e:
    print("lyrics err:", e)

# 5. generate_image_prompt 500 원인 조사
print("\n=== 5. generate_image_prompt ===")
try:
    body = json.dumps({
        "title": "노을빛 마당",
        "poem_body": "마당 구석에 호롱불 켜지고\n어머니의 베틀 소리 들린다.",
        "art_style": "한국적 서정 수채화"
    }).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/api/generate_image_prompt", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print("image_prompt response:", data)
except urllib.error.HTTPError as e:
    print(f"image_prompt HTTPError: {e.code}, body: {e.read().decode('utf-8', errors='ignore')}")
except Exception as e:
    print("image_prompt err:", e)
