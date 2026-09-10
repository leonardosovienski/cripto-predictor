from scripts.scan_secrets import scan


def test_public_atoken_is_not_a_credential_and_json_secrets_are_detected(tmp_path):
    (tmp_path / "contracts.py").write_text("ATOKEN = '0x" + "1" * 40 + "'\n")
    (tmp_path / "reserve.json").write_text('{"a_token":"0x' + "1" * 40 + '"}\n')
    assert scan(tmp_path) == []
    # Synthetic generated values avoid literal credentials in the source itself.
    value = "z" * 32
    (tmp_path / "configuration.json").write_text('{"GEMINI_API_KEY":"' + value + '"}')
    (tmp_path / "camel.py").write_text("accessToken = '" + value + "'")
    findings = scan(tmp_path)
    assert {row["path"] for row in findings} == {"configuration.json", "camel.py"}
    assert all(set(row) == {"path", "line", "kind"} for row in findings)


def test_public_address_exception_never_exempts_api_tokens(tmp_path):
    (tmp_path / "bad.json").write_text('{"api_token":"0x' + "1" * 40 + '"}')
    assert len(scan(tmp_path)) == 1
