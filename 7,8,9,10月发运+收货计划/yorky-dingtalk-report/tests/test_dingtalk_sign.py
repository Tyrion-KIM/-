from dingtalk_sender import sign_dingtalk, build_signed_webhook

# golden vector：由官方算法计算的确定值（secret=SEC000test, ts=1700000000000）
SECRET = "SEC000test"
TS = 1700000000000
EXPECTED_SIGN_URL = "1hLl2KkRX3rps9FaitIUwaac%2BCtAFEaP345jvdrTL7c%3D"


def test_sign_matches_golden_vector():
    assert sign_dingtalk(SECRET, TS) == EXPECTED_SIGN_URL


def test_sign_is_deterministic():
    assert sign_dingtalk(SECRET, TS) == sign_dingtalk(SECRET, TS)


def test_build_signed_webhook():
    base = "https://oapi.dingtalk.com/robot/send?access_token=abc"
    url = build_signed_webhook(base, SECRET, TS)
    assert "timestamp=1700000000000" in url
    assert f"sign={EXPECTED_SIGN_URL}" in url
    assert url.startswith(base)
