"""A test reads the nested value and asserts it, so a missing key fails the assert."""


def test_report_city(report):
    assert report.get("branch", {}).get("city") == "Leeds"
