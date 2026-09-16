from void.models import ModelEngine


def test_tool_argument_parser():
    call = {"function": {"arguments": '{"x": 1}'}}
    assert ModelEngine.parse_tool_arguments(call) == {"x": 1}
