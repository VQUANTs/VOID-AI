from void.providers import OpenAICompatibleProvider, ProviderRegistry
from void.providers.openai_compatible import ProviderModel


def test_registry_static_model():
    registry = ProviderRegistry()
    registry.add_static(ProviderModel(
        id="demo", provider="demo", capabilities=["text", "coding"]
    ))
    assert registry.find("demo").id == "demo"
    assert registry.find("demo:demo").provider == "demo"
