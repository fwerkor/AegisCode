import pytest
from aegiscode.parser import ActionParseError, parse_action

def test_parse_action_from_json():
    action = parse_action('{"action":{"type":"write_file","path":"a.py","content":"x=1"}}')
    assert action.type == "write_file"
    assert action.params["path"] == "a.py"

def test_parse_rejects_non_json():
    with pytest.raises(ActionParseError):
        parse_action('run shell now')
