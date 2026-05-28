from card.validate import (
    validate_color,
    validate_float,
    validate_int,
    validate_linkedin_url,
)


def test_validate_int_clamps_and_defaults():
    assert validate_int("100", 10, 0, 50) == 50
    assert validate_int("-5", 10, 0, 50) == 0
    assert validate_int("25", 10, 0, 50) == 25
    assert validate_int("abc", 10, 0, 50) == 10
    assert validate_int(None, 10, 0, 50) == 10


def test_validate_float_clamps_and_defaults():
    assert validate_float("0.5", 0.52, 0.0, 1.0) == 0.5
    assert validate_float("2", 0.52, 0.0, 1.0) == 1.0
    assert validate_float("-1", 0.52, 0.0, 1.0) == 0.0
    assert validate_float("nope", 0.52, 0.0, 1.0) == 0.52


def test_validate_color_accepts_valid_hex():
    assert validate_color("#0d1117", "#000000") == "#0d1117"
    assert validate_color("ffffff", "#000000") == "#ffffff"
    assert validate_color("#abc", "#000000") == "#abc"
    assert validate_color("#0d1117ff", "#000000") == "#0d1117ff"


def test_validate_color_rejects_bad_length_values():
    assert validate_color("xyz", "#000000") == "#000000"  # no hex chars
    assert validate_color("#12", "#000000") == "#000000"  # 2 digits
    assert validate_color("#1234567", "#000000") == "#000000"  # 7 digits
    assert validate_color("", "#000000") == "#000000"
    assert validate_color(None, "#000000") == "#000000"


def test_validate_color_output_is_always_safe_hex():
    # Even adversarial input can only ever yield a "#"+hex string, never markup.
    result = validate_color("red'/><script>", "#000000")
    assert result.startswith("#")
    assert "<" not in result and ">" not in result
    assert all(c in "0123456789abcdefABCDEF" for c in result[1:])


def test_validate_linkedin_url_accepts_pulse_and_posts():
    assert (
        validate_linkedin_url("https://www.linkedin.com/pulse/my-article")
        == "https://www.linkedin.com/pulse/my-article"
    )
    assert (
        validate_linkedin_url("https://linkedin.com/posts/activity-123")
        == "https://www.linkedin.com/posts/activity-123"
    )


def test_validate_linkedin_url_rejects_bad_input():
    assert validate_linkedin_url("http://www.linkedin.com/pulse/x") == ""
    assert validate_linkedin_url("https://evil.com/pulse/x") == ""
    assert validate_linkedin_url("https://www.linkedin.com/feed/") == ""
    assert validate_linkedin_url("https://user:pass@www.linkedin.com/pulse/x") == ""
