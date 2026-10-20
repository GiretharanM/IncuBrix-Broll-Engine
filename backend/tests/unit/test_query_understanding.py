import pytest
from app.adapters.llm.query_adapter import QueryUnderstandingAdapter

@pytest.fixture
def adapter():
    return QueryUnderstandingAdapter()

def test_ambiguity_bank(adapter):
    # Financial bank
    res_fin = adapter.understand_scene("We deposited our investment revenue in the bank.")
    assert "money" in res_fin["search_query"] or "financial" in res_fin["search_query"]

    # River bank
    res_river = adapter.understand_scene("We sat peacefully on the grass by the bank.")
    assert "river" in res_river["search_query"] or "water" in res_river["search_query"]

def test_ambiguity_cloud(adapter):
    # Tech cloud
    res_tech = adapter.understand_scene("Our software backups are synchronized to the cloud.")
    assert "server" in res_tech["search_query"] or "data" in res_tech["search_query"]

    # Weather cloud
    res_sky = adapter.understand_scene("The storm brought dark rain clouds across the horizon.")
    assert "sky" in res_sky["search_query"] or "clouds" in res_sky["search_query"]

def test_ambiguity_python(adapter):
    # Programming python
    res_prog = adapter.understand_scene("The backend engineer wrote the script in python.")
    assert "code" in res_prog["search_query"] or "programmer" in res_prog["search_query"]

    # Animal python
    res_animal = adapter.understand_scene("The zoo exhibited a massive python.")
    assert "snake" in res_animal["search_query"] or "wild" in res_animal["search_query"]

def test_ambiguity_mouse(adapter):
    # Computer mouse
    res_mouse = adapter.understand_scene("Click the button with your mouse on the screen.")
    assert "computer" in res_mouse["search_query"] or "desk" in res_mouse["search_query"]

def test_abstract_metaphors(adapter):
    res_trust = adapter.understand_scene("Trust is earned slowly and preserved with integrity.")
    assert len(res_trust["metaphors"]) > 0
    assert "shaking hands" in res_trust["search_query"] or "boardroom" in res_trust["search_query"]

    res_work = adapter.understand_scene("Through continuous hard work and dedication, results appear.")
    assert "workshop" in res_work["search_query"] or "craftsman" in res_work["search_query"]

def test_statistics_and_numbers(adapter):
    res_stat = adapter.understand_scene("Over 78.5% of modern enterprises will automate operations.")
    assert res_stat["is_statistic"] is True
    assert "charts" in res_stat["search_query"] or "analytics" in res_stat["search_query"]

    res_dollar = adapter.understand_scene("The project generated over $15 million in savings.")
    assert res_dollar["is_statistic"] is True

def test_named_entity_and_brand_safety(adapter):
    # Elon Musk & Tesla
    res_elon = adapter.understand_scene("Elon Musk unveiled the latest Tesla engineering blueprints.")
    assert res_elon["contains_brand_or_person"] is True
    assert res_elon["safety_warning"] is not None
    assert "Biometric and trademark generation blocked" in res_elon["safety_warning"]
    assert "electric vehicle" in res_elon["search_query"] or "clean transportation" in res_elon["search_query"]

    # Apple
    res_apple = adapter.understand_scene("Apple announced a multi-billion dollar semiconductor facility.")
    assert res_apple["contains_brand_or_person"] is True
    assert res_apple["safety_warning"] is not None
    assert "corporate tech headquarters" in res_apple["search_query"]
