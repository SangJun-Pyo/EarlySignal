import duckdb
import pytest

from es.privacy import privacy_matches, public_text, redact_text, sensitive_values

def test_identifiers_removed_before_sending_and_publication():
    text = "Smoke appeared. VIN: 1HGCM82633A004352. Call (212) 555-0123 or owner@example.com."
    for result in (redact_text(text), public_text(text)):
        assert "1HGCM82633A004352" not in result
        assert "555-0123" not in result
        assert "owner@example.com" not in result
        assert "Smoke appeared." in result
        assert not privacy_matches(result)

def test_public_excerpt_suppresses_entire_sensitive_sentence():
    assert "John" not in public_text("My name is John Smith. The engine stalled.")
    assert "engine stalled" in public_text("My name is John Smith. The engine stalled.")

def test_dates_counts_and_odino_are_not_phone_numbers():
    text = "2018-08-01 complaint #11115234, 16 fires after 120000 miles."
    assert redact_text(text) == text

def test_known_identifiers_removed_as_phrases_without_substring_matches():
    denied = ["Example   Motors", "Exampleville", "1HGCM82633A", "Jane Example"]
    text = "Smoke appeared. EXAMPLE MOTORS in Exampleville saw it. Jane Example drove it. VIN 1HGCM82633A."
    redacted = redact_text(text, denied=denied)
    public = public_text(text, denied=denied)
    for output in (redacted, public):
        assert "Smoke appeared." in output
        assert not privacy_matches(output, denied)
    assert "saw it" not in public
    # City names may be common words; match the complete known phrase only.
    assert redact_text("A washing issue outside Normalville.", denied=["Normal"]) == "A washing issue outside Normalville."
    assert "NORMAL" not in redact_text("In NORMAL the engine stopped.", denied=["Normal"])

def test_sensitive_values_reads_all_component_rows_only_for_requested_ids():
    con = duckdb.connect()
    con.execute("CREATE TABLE complaints_raw(c02 VARCHAR,c15 VARCHAR,c13 VARCHAR,c41 VARCHAR,c42 VARCHAR,c43 VARCHAR,c51 VARCHAR)")
    con.executemany("INSERT INTO complaints_raw VALUES (?,?,?,?,?,?,?)", [
        ("1", "1HGCM82633A", "Exampleville", "Example Motors", "212-555-0123", "Exampleville", "Jane Example"),
        ("1", "1HGCM82633A", "Exampleville", "Second Garage", None, None, None),
        ("2", "OTHER123456", "Otherplace", "Other Garage", None, None, None),
        ("3", "***********", "UNKNOWN", "N/A", None, None, None),
    ])
    values = sensitive_values(con, ["1", "3", "missing", "1"])
    assert set(values) == {"1", "3", "missing"}
    assert {"Example Motors", "Second Garage", "Jane Example", "Exampleville", "1HGCM82633A", "212-555-0123"} == set(values["1"])
    assert values["3"] == [] and values["missing"] == []
    assert sensitive_values(con, []) == {}
    assert sensitive_values(con, ["1' OR 1=1 --"]) == {"1' OR 1=1 --": []}

def test_known_latin_identifiers_with_korean_particles_are_still_private():
    denied = ["Exampleville", "Example Motors", "1HGCM82633A"]
    for text in ("Exampleville에서 연기 발생", "차량을Example Motors에 맡겼다", "1HGCM82633A의 신고"):
        assert privacy_matches(text, denied) == ["known_identifier"]
        assert not privacy_matches(redact_text(text, denied=denied), denied)
        assert public_text(text, denied=denied) == "[식별정보가 포함된 문장 생략]"
    # A different longer Latin name is not the known identifying value.
    assert not privacy_matches("Normalville에서 연기 발생", ["Normal"])
    assert not privacy_matches("Caféville에서 연기 발생", ["Caf"])


@pytest.mark.parametrize("text,redacted", [
    ("a@example.com에서 문의했습니다.", "[REDACTED EMAIL]에서 문의했습니다."),
    ("문의a@example.com", "문의[REDACTED EMAIL]"),
    ("문의a@example.com에서 문의했습니다.", "문의[REDACTED EMAIL]에서 문의했습니다."),
    ("문의(A.User+tag@EXAMPLE.CO.UK)로 연락했습니다.", "문의([REDACTED EMAIL])로 연락했습니다."),
    ("Email user_name@example-domain.com.", "Email [REDACTED EMAIL]."),
])
def test_ascii_email_detection_and_masking_with_korean_neighbors(text, redacted):
    assert privacy_matches(text) == ["email"]
    assert redact_text(text) == redacted
    assert not privacy_matches(redacted)
    assert public_text(text) == "[식별정보가 포함된 문장 생략]"


def test_multiple_korean_adjacent_emails_are_all_masked():
    text = "문의a@example.com이나b@example.org로 연락했습니다."
    assert redact_text(text) == "문의[REDACTED EMAIL]이나[REDACTED EMAIL]로 연락했습니다."
    assert not privacy_matches(redact_text(text))


@pytest.mark.parametrize("text", [
    "문의 이메일 주소는 없습니다.",
    "엔진에서 연기가 발생했습니다.",
    "2018-08-01 신고 #11115234에서 연기가 언급됐습니다.",
    "example.com에서 안내했습니다.",
    "a@example 주소는 이메일 전체 형식이 아닙니다.",
])
def test_ordinary_text_is_unchanged_by_email_boundary_handling(text):
    assert not privacy_matches(text)
    assert redact_text(text) == text
    assert public_text(text) == text
