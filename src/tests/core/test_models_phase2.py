from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.core.models.enums import TokenFrontType, TokenShape, TokenState
from src.core.models.session import Session
from src.core.models.table_token import TableToken
from src.core.models.token import Token


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


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

    _debug_case(
        "Auto UUID generation for Token and Session",
        {
            "token_payload": {
                "name": "Blessing",
                "shape": "CIRCLE",
                "front_type": "IMAGE",
                "front_value": str(front),
                "back_value": str(back),
            }
        },
        {"token.id": "not None", "session.session_id": "not None"},
        {"token.id": str(token.id), "session.session_id": str(session.session_id)},
    )

    assert token.id is not None
    assert session.session_id is not None


def test_token_required_fields_are_validated(tmp_path):
    back = tmp_path / "back.png"
    _create_image_file(back)

    with pytest.raises(ValidationError) as exc_info:
        Token(
            shape=TokenShape.HEXAGON,
            front_type=TokenFrontType.TEXT,
            front_value="Hidden Truth",
            back_value=str(back),
        )

    _debug_case(
        "Token requires mandatory fields",
        {
            "payload": {
                "shape": "HEXAGON",
                "front_type": "TEXT",
                "front_value": "Hidden Truth",
                "back_value": str(back),
            }
        },
        "ValidationError for missing required field: name",
        exc_info.value.errors(),
    )


def test_token_image_paths_are_validated(tmp_path):
    back = tmp_path / "back.png"
    _create_image_file(back)

    with pytest.raises(ValidationError) as missing_front_exc:
        Token(
            name="Curse",
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.IMAGE,
            front_value=str(tmp_path / "missing_front.png"),
            back_value=str(back),
        )

    _debug_case(
        "IMAGE token with missing front image",
        {
            "payload": {
                "name": "Curse",
                "shape": "CIRCLE",
                "front_type": "IMAGE",
                "front_value": str(tmp_path / "missing_front.png"),
                "back_value": str(back),
            }
        },
        "ValidationError for front_value path",
        missing_front_exc.value.errors(),
    )

    front = tmp_path / "front.png"
    _create_image_file(front)

    with pytest.raises(ValidationError) as missing_back_exc:
        Token(
            name="Curse",
            shape=TokenShape.CIRCLE,
            front_type=TokenFrontType.IMAGE,
            front_value=str(front),
            back_value=str(tmp_path / "missing_back.png"),
        )

    _debug_case(
        "Token with missing back image",
        {
            "payload": {
                "name": "Curse",
                "shape": "CIRCLE",
                "front_type": "IMAGE",
                "front_value": str(front),
                "back_value": str(tmp_path / "missing_back.png"),
            }
        },
        "ValidationError for back_value path",
        missing_back_exc.value.errors(),
    )


def test_table_token_coordinates_constraints():
    token_id = uuid4()

    with pytest.raises(ValidationError) as invalid_x_exc:
        TableToken(token_id=token_id, x=-0.1, y=10.0)

    _debug_case(
        "TableToken rejects x below 0",
        {"token_id": str(token_id), "x": -0.1, "y": 10.0},
        "ValidationError for x range [0,100]",
        invalid_x_exc.value.errors(),
    )

    with pytest.raises(ValidationError) as invalid_rotation_exc:
        TableToken(token_id=token_id, x=10.0, y=10.0, rotation=181.0)

    _debug_case(
        "TableToken rejects rotation above 180",
        {"token_id": str(token_id), "x": 10.0, "y": 10.0, "rotation": 181.0},
        "ValidationError for rotation range [0,180]",
        invalid_rotation_exc.value.errors(),
    )

    valid = TableToken(token_id=token_id, x=0.0, y=100.0, z=50.0, rotation=180.0)

    _debug_case(
        "TableToken accepts edge coordinate values",
        {"token_id": str(token_id), "x": 0.0, "y": 100.0, "z": 50.0, "rotation": 180.0},
        {"x": 0.0, "y": 100.0},
        {"x": valid.x, "y": valid.y},
    )

    assert valid.x == 0.0
    assert valid.y == 100.0


def test_table_token_accepts_only_valid_states():
    token_id = uuid4()

    valid = TableToken(token_id=token_id, state=TokenState.FACE_DOWN, x=1.0, y=1.0)
    _debug_case(
        "TableToken accepts enum state",
        {"state": "FACE_DOWN", "x": 1.0, "y": 1.0},
        "state parsed as TokenState.FACE_DOWN",
        str(valid.state),
    )
    assert valid.state == TokenState.FACE_DOWN

    with pytest.raises(ValidationError) as invalid_state_exc:
        TableToken(token_id=token_id, state="INVALID", x=1.0, y=1.0)

    _debug_case(
        "TableToken rejects invalid state",
        {"state": "INVALID", "x": 1.0, "y": 1.0},
        "ValidationError for unsupported state",
        invalid_state_exc.value.errors(),
    )


def test_session_rejects_duplicate_table_tokens():
    token_id = uuid4()
    t1 = TableToken(token_id=token_id, x=10.0, y=10.0)
    t2 = TableToken(token_id=token_id, x=20.0, y=20.0)

    with pytest.raises(ValidationError) as duplicate_token_exc:
        Session(table_tokens=[t1, t2])

    _debug_case(
        "Session rejects duplicate token_id in table_tokens",
        {
            "table_tokens": [
                {"token_id": str(t1.token_id), "x": t1.x, "y": t1.y},
                {"token_id": str(t2.token_id), "x": t2.x, "y": t2.y},
            ]
        },
        "ValidationError for duplicate token_id",
        duplicate_token_exc.value.errors(),
    )
