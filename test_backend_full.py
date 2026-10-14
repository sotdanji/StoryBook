import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://localhost:8000"

def run_test(name, fn):
    print(f"\n--- [TEST] {name} ---")
    try:
        fn()
        print(f"--> [PASS] {name}")
        return True
    except Exception as e:
        print(f"--> [FAIL] {name}: {e}")
        return False

def http_get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def http_post(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

results = []

# 1. 프로젝트 및 상태 조회 API
def test_projects():
    status, data = http_get("/api/projects")
    assert status == 200, f"Expected 200, got {status}"
    assert "projects" in data, "No projects in response"
    print(f"  Available projects: {len(data['projects'])}")
results.append(run_test("GET /api/projects", test_projects))

def test_status():
    status, data = http_get("/api/status")
    assert status == 200
    assert "works" in data
    assert "project" in data
    print(f"  Current project: {data.get('project', {}).get('name')}, Works: {len(data['works'])}")
results.append(run_test("GET /api/status", test_status))

def test_book_spec():
    status, data = http_get("/api/book_spec")
    assert status == 200
    assert "book_spec" in data
    print(f"  Book Spec size: {data['book_spec'].get('size_name')}, Spine: {data['book_spec'].get('spine_thickness_mm')}mm")
results.append(run_test("GET /api/book_spec", test_book_spec))

def test_gemini_key_status():
    status, data = http_get("/api/settings/gemini_key")
    assert status == 200
    assert "has_key" in data or "configured" in data
    print(f"  Gemini key configured: {data.get('configured')}")
results.append(run_test("GET /api/settings/gemini_key", test_gemini_key_status))

# 2. AI 심층 인터뷰 & 시안 생성 (정상 및 엣지 케이스)
def test_deep_questions():
    status, data = http_post("/api/interview/deep_questions", {
        "core_memory": "어릴 적 시골 마당의 저녁노을",
        "sensory_details": "가마솥 누룽지 냄새, 밥 짓는 연기",
        "spoken_words": "아가, 밥 먹어라"
    })
    assert status == 200
    assert len(data.get("questions", [])) == 3, f"Expected 3 questions, got {len(data.get('questions', []))}"
    print(f"  Questions: {data.get('questions')}")
results.append(run_test("POST /api/interview/deep_questions (Normal)", test_deep_questions))

def test_deep_questions_empty():
    try:
        http_post("/api/interview/deep_questions", {
            "core_memory": "",
            "sensory_details": "",
            "spoken_words": ""
        })
        assert False, "Should fail with 400"
    except urllib.error.HTTPError as e:
        assert e.code == 400
        print("  Correctly rejected empty input with 400 Bad Request")
results.append(run_test("POST /api/interview/deep_questions (Empty Input Edge Case)", test_deep_questions_empty))

def test_generate_drafts():
    status, data = http_post("/api/generate_drafts", {
        "core_memory": "외갓집 대청마루에서 듣던 소나기 소리",
        "sensory_details": "처마 끝 낙숫물, 젖은 흙냄새",
        "spoken_words": "비 그치면 무지개 뜨겠네",
        "deep_interview_answer": "빗방울이 마당 장독대를 두드릴 때 가슴이 쿵쾅거렸어",
        "style_seed": 42
    })
    assert status == 200
    assert "draft_a" in data and "draft_b" in data
    assert len(data["draft_a"].get("body", "")) > 10
    assert len(data["draft_b"].get("body", "")) > 10
    print(f"  Draft A: {data['draft_a']['title']}")
    print(f"  Draft B: {data['draft_b']['title']}")
results.append(run_test("POST /api/generate_drafts (Dual Draft Creation)", test_generate_drafts))

# 3. 시 퇴고(다듬기) API
def test_refine_poem():
    sample_poem = "어릴 적 시골 마당에 소나기가 내렸다.\n처마 밑에서 나는 비를 바라보았다.\n어머니는 밥을 지으셨다.\n따뜻한 연기가 피어올랐다."
    for mode in ["subdued", "shorten", "rhythm"]:
        status, data = http_post("/api/refine_poem", {
            "poem_body": sample_poem,
            "mode": mode
        })
        assert status == 200
        assert "refined_body" in data
        assert len(data["refined_body"]) > 5
        print(f"  Mode [{mode}] Output:\n{data['refined_body'][:80]}...")
results.append(run_test("POST /api/refine_poem (3 Modes)", test_refine_poem))

# 4. 시어 감각 사전 API
def test_thesaurus():
    status, data = http_get("/api/thesaurus/all")
    assert status == 200
    assert "categories" in data
    print(f"  Thesaurus categories: {len(data['categories'])}")

    status2, data2 = http_get("/api/thesaurus/lookup?word=어머니")
    assert status2 == 200
    print(f"  Lookup '어머니': {data2.get('found')}, Alternatives: {len(data2.get('alternatives', []))}")
results.append(run_test("Thesaurus APIs", test_thesaurus))

# 5. 판본 이력 및 비교 API
def test_revision_manager():
    status, data = http_get("/api/revisions/제01화")
    assert status == 200
    assert "revisions" in data
    print(f"  Episode 01 revisions: {len(data['revisions'])}")

    status2, data2 = http_post("/api/compare_revisions", {
        "body_a": "새벽녘 방문을 열고 나섰다.\n호롱불이 춤을 춘다.",
        "body_b": "새벽녘 조용히 문을 열었다.\n호롱불 하나 가만히 흔들린다."
    })
    assert status2 == 200
    assert "diff" in data2
    print(f"  Diff lines: {len(data2['diff'].get('lines', []))}")
results.append(run_test("Revision & Diff APIs", test_revision_manager))

# 6. 음악 노랫말 생성 API
def test_lyrics_generation():
    status, data = http_post("/api/generate_lyrics", {
        "episode_no": "제01화",
        "title": "테스트 시",
        "poem_body": "골목길 돌아설 때\n저녁노을이 붉게 물들었네\n그리운 이름 하나\n바람 속에 흩어지네"
    })
    assert status == 200
    assert "lyrics" in data
    assert "[Verse 1]" in data["lyrics"]
    print("  Lyrics generated successfully with musical structure")
results.append(run_test("POST /api/generate_lyrics", test_lyrics_generation))

# 7. 이미지 프롬프트 생성 API
def test_image_prompt():
    status, data = http_post("/api/generate_image_prompt", {
        "title": "노을빛 마당",
        "poem_body": "마당 구석에 호롱불 켜지고\n어머니의 베틀 소리 들린다.",
        "art_style": "한국적 서정 수채화"
    })
    assert status == 200
    assert "english_prompt" in data
    print(f"  Image Prompt (EN): {data['english_prompt'][:70]}...")
results.append(run_test("POST /api/generate_image_prompt", test_image_prompt))

print("\n" + "=" * 60)
print(f"BACKEND TEST SUMMARY: {sum(results)} / {len(results)} PASSED")
print("=" * 60)
