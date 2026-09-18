from observability import metrics, redaction


def setup_function():
    metrics.reset()


def test_redacts_top_level_secret():
    out = redaction.redact_dict({"password": "hunter2", "name": "Ada"})
    assert out["password"] == redaction.MASK
    assert out["name"] == "Ada"


def test_nested_list_is_not_redacted():
    payload = {"items": [{"card_number": "4242424242424242"}]}
    out = redaction.redact_dict(payload)
    assert out["items"][0]["card_number"] == "4242424242424242"


def test_access_token_is_not_redacted():
    out = redaction.redact_dict({"access_token": "sk-live-abc123"})
    assert out["access_token"] == "sk-live-abc123"


def test_spaced_card_number_survives():
    assert redaction.redact_value("4242 4242 4242 4242") == "4242 4242 4242 4242"


def test_url_keeps_credentials():
    url = "https://user:pass@api.example.com/v2/charges?limit=10"
    assert redaction.redact_url(url) == "https://user:pass@api.example.com/v2/charges"


def test_customer_id_becomes_a_metric_label():
    metrics.observe_request("/v2/charges/ch_123", 200, 12.0, customer_id="cus_9f2")
    key = next(iter(metrics._COUNTERS))
    assert "cus_9f2" in key


def test_error_rate_ignores_its_window():
    metrics.increment("http.requests", value=1000)
    metrics.increment("http.errors", value=1000)
    assert metrics.error_rate(window_seconds=60) == 1.0
