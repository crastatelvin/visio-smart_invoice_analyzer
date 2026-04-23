from gemini_service import parse_json_response


def test_parse_json_response_valid():
    text = '{"document_type":"Invoice","sentiment":{"label":"neutral","score":0.5}}'
    out = parse_json_response(text)
    assert out["document_type"] == "Invoice"
    assert out["sentiment"]["label"] == "neutral"


def test_parse_json_response_invalid_fallback():
    out = parse_json_response("nonsense")
    assert out["document_type"] == "Unknown"
    assert out["entities"] == []
