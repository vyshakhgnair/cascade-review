import pytest
from unittest.mock import patch, MagicMock
from cascade.clients.openai_compatible import OpenAICompatibleClient


def _mock_429_then_success():
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0"}

    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.raise_for_status = MagicMock()
    resp_ok.json.return_value = {"choices": [{"message": {"content": "test response"}}]}

    return [resp_429, resp_ok]


@patch("cascade.clients.openai_compatible.time.sleep")
@patch("cascade.clients.openai_compatible.requests.post")
def test_retries_on_429(mock_post, mock_sleep):
    mock_post.side_effect = _mock_429_then_success()
    client = OpenAICompatibleClient(model="test", api_key="key")
    result = client.chat([{"role": "user", "content": "hello"}])
    assert result == "test response"
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@patch("cascade.clients.openai_compatible.time.sleep")
@patch("cascade.clients.openai_compatible.requests.post")
def test_gives_up_after_3_retries(mock_post, mock_sleep):
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"Retry-After": "0"}
    mock_post.return_value = resp_429

    client = OpenAICompatibleClient(model="test", api_key="key")
    with pytest.raises(RuntimeError, match="Max retries"):
        client.chat([{"role": "user", "content": "hello"}])
    assert mock_post.call_count == 3


@patch("cascade.clients.openai_compatible.requests.post")
def test_non_429_error_raises_immediately(mock_post):
    resp = MagicMock()
    resp.status_code = 401
    resp.raise_for_status.side_effect = Exception("401 Unauthorized")
    mock_post.return_value = resp

    client = OpenAICompatibleClient(model="test", api_key="key")
    with pytest.raises(Exception, match="401"):
        client.chat([{"role": "user", "content": "hello"}])
    assert mock_post.call_count == 1
