import pytest

from src.infrastructure.deck_adapter.exceptions import (
    DeckEmptyError,
    DuplicateTokenIdError,
    InvalidDrawCountError,
)
from src.infrastructure.deck_adapter.token_deck import TokenDeck


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


def test_shuffle_is_deterministic_with_same_seed():
    token_ids = ["t1", "t2", "t3", "t4", "t5"]

    deck_a = TokenDeck(token_ids=token_ids, seed=42)
    deck_b = TokenDeck(token_ids=token_ids, seed=42)

    order_a = deck_a.peek_all()
    order_b = deck_b.peek_all()

    _debug_case(
        "Deterministic shuffle with same seed",
        {"token_ids": token_ids, "seed": 42},
        {"order_a": "same as order_b"},
        {"order_a": order_a, "order_b": order_b},
    )

    assert order_a == order_b


def test_draw_one_returns_token_and_decreases_remaining_count():
    deck = TokenDeck(token_ids=["a", "b", "c"], seed=7)
    remaining_before = deck.remaining_count()
    drawn = deck.draw_one()
    remaining_after = deck.remaining_count()

    _debug_case(
        "draw_one extracts one token",
        {"remaining_before": remaining_before},
        {"drawn": "one token id", "remaining_after": remaining_before - 1},
        {"drawn": drawn, "remaining_after": remaining_after},
    )

    assert drawn in {"a", "b", "c"}
    assert remaining_after == remaining_before - 1


def test_draw_many_returns_k_tokens_and_decreases_count():
    deck = TokenDeck(token_ids=["a", "b", "c", "d"], seed=9)
    drawn = deck.draw_many(3)

    _debug_case(
        "draw_many extracts requested number of tokens",
        {"k": 3, "remaining_before": 4},
        {"len(drawn)": 3, "remaining_after": 1},
        {"drawn": drawn, "remaining_after": deck.remaining_count()},
    )

    assert len(drawn) == 3
    assert len(set(drawn)) == 3
    assert deck.remaining_count() == 1


def test_draw_from_empty_deck_raises_error():
    deck = TokenDeck(token_ids=["only"], seed=1)
    first_draw = deck.draw_one()

    _debug_case(
        "Prepare empty deck",
        {"initial_tokens": ["only"]},
        {"first_draw": "only", "deck_empty": True},
        {"first_draw": first_draw, "deck_empty": deck.is_empty()},
    )

    with pytest.raises(DeckEmptyError) as exc_info:
        deck.draw_one()

    _debug_case(
        "draw_one on empty deck raises",
        {"remaining": deck.remaining_count()},
        "DeckEmptyError",
        str(exc_info.value),
    )


def test_draw_many_invalid_count_raises_error():
    deck = TokenDeck(token_ids=["a", "b"], seed=10)

    with pytest.raises(InvalidDrawCountError) as exc_info:
        deck.draw_many(0)

    _debug_case(
        "draw_many validates k > 0",
        {"k": 0},
        "InvalidDrawCountError",
        str(exc_info.value),
    )


def test_duplicate_token_ids_not_allowed():
    with pytest.raises(DuplicateTokenIdError) as exc_info:
        TokenDeck(token_ids=["dup", "dup"], seed=12)

    _debug_case(
        "Deck rejects duplicated token IDs",
        {"token_ids": ["dup", "dup"]},
        "DuplicateTokenIdError",
        str(exc_info.value),
    )
