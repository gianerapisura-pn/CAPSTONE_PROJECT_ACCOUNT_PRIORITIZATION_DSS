from unittest.mock import MagicMock

import pytest

from scripts import check_password_safety as screening


@pytest.mark.parametrize("body,expected", [
    (b"1E4C9B93F3F0682250B6CF8331B7EE68FD8:123\r\n", True),
    (b"1E4C9B93F3F0682250B6CF8331B7EE68FD8:0", False),
    (b"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:1", False),
])
def test_provisioning_range_lookup_is_private(monkeypatch, body, expected):
    response = MagicMock(status=200)
    response.read.return_value = body
    response.__enter__.return_value = response
    opener = MagicMock(return_value=response)
    monkeypatch.setattr(screening, "urlopen", opener)
    assert screening.is_compromised("password") is expected
    request = opener.call_args.args[0]
    assert request.full_url == "https://api.pwnedpasswords.com/range/5BAA6"
    assert request.data is None
    assert request.get_header("Add-padding") == "true"
    assert opener.call_args.kwargs["timeout"] == 8


@pytest.mark.parametrize("body", [b"", b"<html>Unavailable</html>", b"A:1", b"A" * 1_000_001], ids=["empty", "html", "invalid", "oversized"])
def test_invalid_response_does_not_pass(monkeypatch, body):
    response = MagicMock(status=200)
    response.read.return_value = body
    response.__enter__.return_value = response
    monkeypatch.setattr(screening, "urlopen", MagicMock(return_value=response))
    with pytest.raises(ValueError):
        screening.is_compromised("password")


@pytest.mark.parametrize("result,exit_code", [(True, 1), (False, 0), (TimeoutError(), 2)])
def test_provisioning_command_handles_results_without_printing_password(monkeypatch, capsys, result, exit_code):
    password = "Synthetic Example 42!"
    monkeypatch.setattr(screening, "getpass", lambda _prompt: password)
    def check(value):
        assert value == password
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(screening, "is_compromised", check)
    assert screening.main() == exit_code
    assert password not in capsys.readouterr().out
