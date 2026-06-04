def test_health_status_colors():
    mapping = {
        "normal": "green",
        "warning": "yellow",
        "alarm": "red",
    }
    for status, color in mapping.items():
        assert status in ("normal", "warning", "alarm")
        assert color in ("green", "yellow", "red")
