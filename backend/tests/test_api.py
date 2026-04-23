from fastapi.testclient import TestClient
import main


client = TestClient(main.app)


def test_root():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "VISIO ONLINE"


def test_scan_rejects_unsupported_file():
    res = client.post(
        "/scan",
        files={"file": ("bad.exe", b"abcd", "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "Unsupported" in res.json()["error"]
