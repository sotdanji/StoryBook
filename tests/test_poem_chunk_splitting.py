import pytest
from core.bookk_pdf_builder import BookkPDFBuilder

@pytest.fixture
def builder():
    return BookkPDFBuilder()

SAMPLE_POEM = [
    "새벽녘",
    "오줌 마려워 방문을 열고 나섰다.",
    "윗채 대청마루에서",
    "베틀이 노래를 부르고 있었다.",
    "",
    "호롱불 하나 흔들흔들 춤을 추고",
    "베틀에 앉은 어머니의 등도 흔들거렸다.",
    "",
    "북통이 스르륵 스르륵",
    "왼쪽에서 오른쪽으로",
    "스르륵 탁,",
    "바디질 소리가 고요한 새벽 공기를 갈랐다.",
    "",
    "달빛보다 서늘한 창호지 문살 너머",
    "가느다란 실오라기들이 모여",
    "어머니의 시름을 감싸 안고",
    "한 올 한 올 하얀 무명천이 되어 갔다.",
    "",
    "어머니, 춥지 않으세요?",
    "차마 묻지 못하고 문설주 뒤에 숨어",
    "새근새근 베틀 소리만 가슴에 담았다."
]

def test_split_count_one(builder):
    """count가 1일 때는 전체 시를 단일 청크로 반환해야 한다."""
    chunks = builder._split_poem_into_n_chunks(SAMPLE_POEM, 1)
    assert len(chunks) == 1
    assert chunks[0] == SAMPLE_POEM

def test_split_count_two(builder):
    """count가 2일 때는 2개 청크로 분할되며, 모든 줄이 온전히 보존되어야 한다."""
    chunks = builder._split_poem_into_n_chunks(SAMPLE_POEM, 2)
    assert len(chunks) == 2
    
    clean_original = [ln.strip() for ln in SAMPLE_POEM if ln.strip()]
    clean_combined = []
    for c in chunks:
        clean_combined.extend([ln.strip() for ln in c if ln.strip()])
    assert clean_combined == clean_original

def test_split_count_three(builder):
    """count가 3일 때는 3개 청크로 지능형 분할되어야 한다 (3페이지 장시 지원)."""
    chunks = builder._split_poem_into_n_chunks(SAMPLE_POEM, 3)
    assert len(chunks) == 3
    for idx, c in enumerate(chunks):
        assert len(c) > 0, f"청크 {idx+1}이 비어있습니다."
    
    clean_original = [ln.strip() for ln in SAMPLE_POEM if ln.strip()]
    clean_combined = []
    for c in chunks:
        clean_combined.extend([ln.strip() for ln in c if ln.strip()])
    assert clean_combined == clean_original

def test_split_count_four(builder):
    """count가 4일 때는 4개 청크로 분할되어 4페이지 연속 서사시를 지원해야 한다."""
    chunks = builder._split_poem_into_n_chunks(SAMPLE_POEM, 4)
    assert len(chunks) == 4
    for idx, c in enumerate(chunks):
        assert len(c) > 0, f"청크 {idx+1}이 비어있습니다."
    
    clean_original = [ln.strip() for ln in SAMPLE_POEM if ln.strip()]
    clean_combined = []
    for c in chunks:
        clean_combined.extend([ln.strip() for ln in c if ln.strip()])
    assert clean_combined == clean_original

def test_split_short_poem_safety(builder):
    """6줄 이하의 짧은 시는 무리하게 쪼개지 않고 안전하게 단일 청크로 유지한다."""
    short_poem = ["꽃 하나 피어나고", "바람이 분다.", "봄이 왔다."]
    chunks = builder._split_poem_into_n_chunks(short_poem, 3)
    assert len(chunks) == 1
    assert chunks[0] == short_poem

def test_split_empty_poem_safety(builder):
    """빈 리스트가 들어와도 에러 없이 안전하게 처리한다."""
    chunks = builder._split_poem_into_n_chunks([], 2)
    assert len(chunks) == 1
    assert chunks[0] == []
