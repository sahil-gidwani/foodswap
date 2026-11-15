"""Types shared by the request parser, the constraint checks and the ranker."""

from dataclasses import dataclass
from enum import IntEnum


class Verdict(IntEnum):
    FAIL = 0
    PASS = 1
    UNKNOWN = 2  # the record doesn't have enough information to decide


@dataclass(frozen=True)
class Constraint:
    kind: str  # "allergen", "ingredient", "max" or "min"
    target: str  # "peanuts", "en:gelatin", "sugars"
    value: float | None = None  # grams per 100 g or 100 ml, for "max" and "min"


@dataclass(frozen=True)
class NutrientGoal:
    nutrient: str  # "sugars"
    direction: int  # -1 for less, +1 for more


@dataclass(frozen=True)
class ParsedRequest:
    raw: str
    type_terms: tuple[str, ...] = ()  # "cereal"
    type_category: str | None = None  # category the type terms resolve to, e.g. "en:breakfast-cereals"
    residual_terms: tuple[str, ...] = ()  # other words that stay in the search query
    hard: tuple[Constraint, ...] = ()
    goals: tuple[NutrientGoal, ...] = ()
    negated_terms: tuple[str, ...] = ()  # excluded words; never searched for
    clarifications: tuple[str, ...] = ()  # questions to show the user
