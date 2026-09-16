from void.router import ModelRouter


def test_route_inference():
    assert ModelRouter.infer_route("write Python code") == "coding"
    assert ModelRouter.infer_route("what is the latest news?") == "research"
    assert ModelRouter.infer_route("analyze this screenshot") == "vision"
    assert ModelRouter.infer_route("explain this deeply") == "reasoning"
