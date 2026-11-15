import pytest

from foodswap.allergens import ALLERGENS, check, ingredient_allergens
from foodswap.schema import Verdict

# A tiny ingredient taxonomy with the same shape as Open Food Facts': properties sit on a few
# parent nodes and are inherited by everything below them.
TAXONOMY = {
    "en:dairy": {"allergens": {"en": "en:milk"}},
    "en:whey": {"parents": ["en:dairy"]},
    "en:cereal": {},
    "en:wheat": {"parents": ["en:cereal"], "allergens": {"en": "en:gluten"}},
    "en:wheat-flour": {"parents": ["en:wheat"]},
    "en:barley": {"parents": ["en:cereal"], "allergens": {"en": "en:gluten"}},
    "en:oat": {"parents": ["en:cereal"]},
    "en:sugar": {},
}
CARRIED = ingredient_allergens(TAXONOMY)


def product(text="sugar, oats", tags=(), traces=(), ingredients=("en:sugar",), n=2, unknown=0):
    return {
        "ingredients_text": text,
        "allergen_tags": list(tags),
        "trace_tags": list(traces),
        "ingredient_tags": list(ingredients),
        "ingredients_n": n,
        "unknown_ingredients_n": unknown,
    }


def verdict(p, allergen):
    return check(p, allergen, CARRIED)[0]


def test_allergens_are_inherited_through_the_taxonomy():
    assert CARRIED["en:whey"] == {"milk"}
    assert CARRIED["en:wheat-flour"] == {"wheat", "gluten"}
    assert CARRIED["en:barley"] == {"gluten"}  # barley is gluten but not wheat
    assert "en:oat" not in CARRIED


@pytest.mark.parametrize(
    "p, source",
    [
        (product(tags=["en:milk"]), "allergen list"),
        (product(traces=["en:milk"]), "may contain"),
        (product(text="sugar, whey powder", ingredients=["en:whey"]), "ingredient"),
        (product(text="sugar, milk powder"), "ingredient text"),
    ],
)
def test_any_source_is_enough_to_fail(p, source):
    v, evidence = check(p, "milk", CARRIED)
    assert v == Verdict.FAIL
    assert source in [s for s, _ in evidence]


def test_clean_record_passes():
    assert verdict(product(), "milk") == Verdict.PASS


@pytest.mark.parametrize(
    "p, reason",
    [
        (product(text=None), "no_ingredients"),
        (product(n=0), "not_parsed"),
        (product(n=10, unknown=5), "low_recognition"),
    ],
)
def test_missing_information_is_unknown_not_pass(p, reason):
    assert check(p, "peanuts", CARRIED) == (Verdict.UNKNOWN, [("missing", reason)])


def test_evidence_beats_missing_information():
    assert verdict(product(text=None, tags=["en:peanuts"]), "peanuts") == Verdict.FAIL


def test_gluten_tag_counts_as_possible_wheat():
    assert verdict(product(tags=["en:gluten"]), "wheat") == Verdict.FAIL


@pytest.mark.parametrize(
    "allergen, text",
    [
        ("milk", "coconut milk, almondmilk, oat milk"),
        ("milk", "cocoa butter, almond butter, peanut butter, sunflower butter"),
        ("milk", "cream of tartar, coconut cream"),
        ("eggs", "eggplant"),
        ("tree_nuts", "coconut, nutmeg, doughnut, butternut squash, water chestnut"),
        ("tree_nuts", "soy nuts, corn nuts, peanuts"),
        ("wheat", "buckwheat flour, rice flour, mustard flour"),
        ("wheat", "gluten free flour blend (rice flour, tapioca starch)"),
        ("gluten", "maltodextrin, maltose, gluten-free oats"),
        ("peanuts", "made in a peanut free facility"),
        ("soybeans", "soy-free, sunflower lecithin"),
        ("fish", "crustacean shellfish"),
    ],
)
def test_lookalikes_do_not_match(allergen, text):
    assert verdict(product(text=text), allergen) == Verdict.PASS


@pytest.mark.parametrize(
    "allergen, text",
    [
        ("milk", "milkpowder, butterfat"),
        ("milk", "nonfat dry milk"),
        ("milk", "lactalbumin"),
        ("eggs", "preservative: lysozyme"),
        ("fish", "whitefish roe"),
        ("tree_nuts", "pistachionut"),
        ("peanuts", "peanutbutter"),
        ("soybeans", "organic soymilk, soybeanoil"),
        ("sesame", "toasted sesameoil"),
        ("wheat", "flour, sugar, water"),
        ("wheat", "enriched bleached flour (niacin, iron)"),
        ("gluten", "malt vinegar"),
    ],
)
def test_real_mentions_match(allergen, text):
    assert verdict(product(text=text), allergen) == Verdict.FAIL


def test_every_allergen_has_a_tag_or_root():
    for name, spec in ALLERGENS.items():
        assert spec["tags"] or spec.get("root"), name
