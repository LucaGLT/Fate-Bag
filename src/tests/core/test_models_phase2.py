from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.core.models.enums import TokenFrontType, TokenShape, TokenState
from src.core.models.session import Session
from src.core.models.table_token import TableToken
from src.core.models.token import Token


def _create_image_file(path):
    path.write_bytes(b"fake-image")


def test_token_and_session_auto_id(tmp_path):
    front = tmp_path / "front.png"
    back = tmp_path / "back.png"
    _create_image_file(front)
    _create_image_file(back)

    token = Token(
        name="Blessing",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.IMAGE,
        front_value=str(front),
        back_value=str(back),
    )
    session = Session()

    assert token.id is not None
    assert session.session_id is not None


def test_token_required_fields_are_validated(tmp_path):
    back = tmp_path / "back.png"
    _create_image_file(back)

    with pytest.raises(ValidationError):
        Token(
            shape=TokenShape.HEXAGON,
            front_type=TokenFrontType.TEXT,
            front_value="Hidden Truth",
            back_value=str(back),
        )


def test_token_image_paths_are_validated(tmp_path):
    back = tmp_path / "back.png"
    _create_image_file(back)

    with pytest.raises(ValidationError):
        Token(
            name="Curse",
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.IMAGE,
            front_value=str(tmp_path / "missing_front.png"),
            back_value=str(back),
        )

    front = tmp_path / "front.png"
    _create_image_file(front)

    with pytest.raises(ValidationError):
        Token(
            name="Curse",
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.IMAGE,
            front_value=str(front),
            back_value=str(tmp_path / "missing_back.png"),
        )


def test_table_token_coordinates_constraints():
    token_id = uuid4()

    with pytest.raises(ValidationError):
        TableToken(token_id=token_id, x=-0.1, y=10.0)

    with pytest.raises(ValidationError):
        TableToken(token_id=token_id, x=10.0, y=10.0, rotation=181.0)

    valid = TableToken(token_id=token_id, x=0.0, y=100.0, z=50.0, rotation=180.0)
    assert valid.x == 0.0
    assert valid.y == 100.0


def test_table_token_accepts_only_valid_states():
    token_id = uuid4()

    valid = TableToken(token_id=token_id, state=TokenState.FACE_DOWN, x=1.0, y=1.0)
    assert valid.state == TokenState.FACE_DOWN

    with pytest.raises(ValidationError):
        TableToken(token_id=token_id, state="INVALID", x=1.0, y=1.0)


def test_session_rejects_duplicate_table_tokens():
    token_id = uuid4()
    t1 = TableToken(token_id=token_id, x=10.0, y=10.0)
    t2 = TableToken(token_id=token_id, x=20.0, y=20.0)

    with pytest.raises(ValidationError):
        Session(table_tokens=[t1, t2])
