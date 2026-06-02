from uuid import UUID

import pytest

from src.core.engine.draw_engine import DrawEngine
from src.core.engine.session_engine import SessionEngine
from src.core.engine.shuffle_engine import ShuffleEngine
from src.core.models.enums import TokenFrontType, TokenShape, TokenState
from src.core.models.token import Token


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


def _build_tokens(tmp_path):
    back = tmp_path / "back.png"
    back.write_bytes(b"fake-image")

    def make_token(name, categories, tags, weight, rarity):
        return Token(
            name=name,
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.TEXT,
            front_value=name,
            back_value=str(back),
            categories=categories,
            tags=tags,
            weight=weight,
            rarity=rarity,
        )

    return [
        make_token("Blessing", ["holy"], ["light"], 5.0, "common"),
        make_token("Curse", ["shadow"], ["dark"], 1.0, "rare"),
        make_token("Shield", ["holy"], ["defense"], 2.0, "common"),
        make_token("Doom", ["shadow"], ["dark"], 0.5, "legendary"),
    ]


def test_session_creation_filters_selection_and_exclusion(tmp_path):
    tokens = _build_tokens(tmp_path)
    engine = SessionEngine(tokens)

    selected_ids = [tokens[0].id, tokens[1].id, tokens[2].id]
    excluded_ids = [tokens[1].id]
    session = engine.create_session(
        use_token_ids=selected_ids,
        exclude_token_ids=excluded_ids,
        category="holy",
    )

    final_ids = [table_token.token_id for table_token in session.table_tokens]
    states = [table_token.state for table_token in session.table_tokens]

    _debug_case(
        "Session creation with use_token_ids + exclude_token_ids + category",
        {
            "use_token_ids": [str(token_id) for token_id in selected_ids],
            "exclude_token_ids": [str(token_id) for token_id in excluded_ids],
            "category": "holy",
        },
        {
            "table_size": 2,
            "states": [TokenState.FACE_DOWN.value, TokenState.FACE_DOWN.value],
        },
        {
            "table_size": len(final_ids),
            "token_ids": [str(token_id) for token_id in final_ids],
            "states": [state.value for state in states],
        },
    )

    assert len(final_ids) == 2
    assert tokens[0].id in final_ids
    assert tokens[2].id in final_ids
    assert all(state == TokenState.FACE_DOWN for state in states)


def test_random_subset_is_deterministic_with_seed(tmp_path):
    tokens = _build_tokens(tmp_path)
    engine = SessionEngine(tokens)

    session_a = engine.use_random_subset(2, seed=77)
    session_b = engine.use_random_subset(2, seed=77)

    ids_a = [str(table_token.token_id) for table_token in session_a.table_tokens]
    ids_b = [str(table_token.token_id) for table_token in session_b.table_tokens]

    _debug_case(
        "Random subset deterministic by seed",
        {"subset_size": 2, "seed": 77},
        {"ids_a": "same as ids_b"},
        {"ids_a": ids_a, "ids_b": ids_b},
    )

    assert ids_a == ids_b


def test_draw_uniform_with_and_without_replacement(tmp_path):
    tokens = _build_tokens(tmp_path)
    session_engine = SessionEngine(tokens)
    draw_engine = DrawEngine(tokens)

    session = session_engine.use_all_tokens(seed=13)

    drawn_no_replacement = draw_engine.draw_uniform(session, count=2, with_replacement=False, seed=5)
    drawn_with_replacement = draw_engine.draw_uniform(session, count=3, with_replacement=True, seed=5)

    _debug_case(
        "Uniform draw modes",
        {"count_no_replacement": 2, "count_with_replacement": 3, "seed": 5},
        {"history_size": 5, "selected_states": "drawn tokens marked SELECTED"},
        {
            "drawn_no_replacement": [str(token_id) for token_id in drawn_no_replacement],
            "drawn_with_replacement": [str(token_id) for token_id in drawn_with_replacement],
            "history_size": len(session.draw_history),
        },
    )

    assert len(drawn_no_replacement) == 2
    assert len(set(drawn_no_replacement)) == 2
    assert len(drawn_with_replacement) == 3
    assert len(session.draw_history) == 5


def test_draw_weighted_and_by_rarity(tmp_path):
    tokens = _build_tokens(tmp_path)
    session = SessionEngine(tokens).use_all_tokens(seed=31)
    draw_engine = DrawEngine(tokens)

    weighted = draw_engine.draw_weighted(session, count=2, with_replacement=False, seed=99)
    rarity_draw = draw_engine.draw_by_rarity(
        session,
        rarity="common",
        count=1,
        with_replacement=False,
        seed=2,
    )

    _debug_case(
        "Weighted draw + rarity draw",
        {"weighted_count": 2, "rarity": "common", "seed_weighted": 99, "seed_rarity": 2},
        {"weighted_len": 2, "rarity_len": 1, "rarity_token_in_common": True},
        {
            "weighted": [str(token_id) for token_id in weighted],
            "rarity_draw": [str(token_id) for token_id in rarity_draw],
        },
    )

    common_ids = {token.id for token in tokens if token.rarity == "common"}
    assert len(weighted) == 2
    assert len(rarity_draw) == 1
    assert rarity_draw[0] in common_ids

    with pytest.raises(ValueError) as exc_info:
        draw_engine.draw_by_rarity(session, rarity="mythic", count=1)

    _debug_case(
        "Rarity draw with missing rarity",
        {"rarity": "mythic"},
        "ValueError",
        str(exc_info.value),
    )


def test_reveal_hide_reset_and_shuffle(tmp_path):
    tokens = _build_tokens(tmp_path)
    session_engine = SessionEngine(tokens)
    draw_engine = DrawEngine(tokens)
    shuffle_engine = ShuffleEngine()

    session = session_engine.use_all_tokens(seed=1)

    revealed = draw_engine.reveal_tokens(session)
    states_after_reveal = [table_token.state for table_token in session.table_tokens]

    hidden = draw_engine.hide_tokens(session)
    states_after_hide = [table_token.state for table_token in session.table_tokens]

    draw_engine.draw_uniform(session, count=2, with_replacement=False, seed=11)
    session_engine.reset_session(session)

    before_shuffle = [table_token.token_id for table_token in session.table_tokens]
    shuffle_engine.shuffle(session, seed=123)
    after_shuffle = [table_token.token_id for table_token in session.table_tokens]

    _debug_case(
        "Reveal/Hide/Reset/Shuffle",
        {"session_size": len(session.table_tokens), "shuffle_seed": 123},
        {
            "all_revealed": True,
            "all_hidden_after_hide": True,
            "history_after_reset": 0,
            "order_changed_or_seed_applied": True,
        },
        {
            "revealed_count": len(revealed),
            "hidden_count": len(hidden),
            "all_revealed": all(state == TokenState.FACE_UP for state in states_after_reveal),
            "all_hidden_after_hide": all(state == TokenState.FACE_DOWN for state in states_after_hide),
            "history_after_reset": len(session.draw_history),
            "before_shuffle": [str(token_id) for token_id in before_shuffle],
            "after_shuffle": [str(token_id) for token_id in after_shuffle],
        },
    )

    assert len(revealed) == len(session.table_tokens)
    assert all(state == TokenState.FACE_UP for state in states_after_reveal)
    assert all(state == TokenState.FACE_DOWN for state in states_after_hide)
    assert len(session.draw_history) == 0
    assert sorted(before_shuffle) == sorted(after_shuffle)


def test_session_creation_rejects_unknown_token_id(tmp_path):
    tokens = _build_tokens(tmp_path)
    engine = SessionEngine(tokens)

    unknown_id = UUID("00000000-0000-0000-0000-000000000123")

    with pytest.raises(ValueError) as exc_info:
        engine.use_token_ids([unknown_id])

    _debug_case(
        "Session creation rejects unknown token IDs",
        {"use_token_ids": [str(unknown_id)]},
        "ValueError for unknown IDs",
        str(exc_info.value),
    )
