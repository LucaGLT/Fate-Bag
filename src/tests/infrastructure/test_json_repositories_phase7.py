from src.core.models.enums import TokenFrontType, TokenShape, TokenState
from src.core.models.session import Session
from src.core.models.table_token import TableToken
from src.core.models.token import Token
from src.infrastructure.json.json_session_repository import JsonSessionRepository
from src.infrastructure.json.json_token_repository import JsonTokenRepository


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


def _build_token(tmp_path, name: str) -> Token:
    back = tmp_path / "back.png"
    back.write_bytes(b"fake-image")

    return Token(
        name=name,
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value=name,
        back_value=str(back),
        categories=["holy"],
        tags=["demo"],
        weight=1.5,
        rarity="common",
    )


def test_json_token_repository_save_load_and_integrity(tmp_path):
    repo = JsonTokenRepository(tmp_path / "tokens.json")

    token_a = _build_token(tmp_path, "Blessing")
    token_b = _build_token(tmp_path, "Shield")

    repo.save(token_a)
    repo.save(token_b)

    loaded_all = repo.get_all()
    loaded_one = repo.get_by_id(token_a.id)

    _debug_case(
        "Token repository save/load",
        {"saved_ids": [str(token_a.id), str(token_b.id)]},
        {"count": 2, "first_name": "Blessing"},
        {
            "count": len(loaded_all),
            "loaded_one_name": loaded_one.name if loaded_one else None,
            "loaded_ids": [str(token.id) for token in loaded_all],
        },
    )

    assert len(loaded_all) == 2
    assert loaded_one is not None
    assert loaded_one.name == "Blessing"

    repo.delete(token_b.id)
    after_delete = repo.get_all()

    _debug_case(
        "Token repository delete",
        {"deleted_id": str(token_b.id)},
        {"remaining_count": 1},
        {"remaining_count": len(after_delete), "remaining_ids": [str(token.id) for token in after_delete]},
    )

    assert len(after_delete) == 1


def test_json_session_repository_save_load_and_integrity(tmp_path):
    repo = JsonSessionRepository(tmp_path / "sessions.json")

    token = _build_token(tmp_path, "Curse")
    table_token = TableToken(token_id=token.id, state=TokenState.FACE_DOWN, x=10.0, y=20.0)
    session = Session(seed=42, table_tokens=[table_token], draw_history=[token.id])

    repo.save(session)
    loaded = repo.load(session.session_id)

    _debug_case(
        "Session repository save/load",
        {
            "session_id": str(session.session_id),
            "seed": 42,
            "table_tokens": 1,
            "draw_history": [str(token.id)],
        },
        {"loaded_seed": 42, "loaded_table_tokens": 1, "loaded_history": 1},
        {
            "loaded_seed": loaded.seed if loaded else None,
            "loaded_table_tokens": len(loaded.table_tokens) if loaded else None,
            "loaded_history": len(loaded.draw_history) if loaded else None,
        },
    )

    assert loaded is not None
    assert loaded.seed == 42
    assert len(loaded.table_tokens) == 1
    assert loaded.draw_history == [token.id]

    repo.delete(session.session_id)
    missing = repo.load(session.session_id)

    _debug_case(
        "Session repository delete",
        {"deleted_session_id": str(session.session_id)},
        {"loaded_after_delete": None},
        {"loaded_after_delete": missing},
    )

    assert missing is None
