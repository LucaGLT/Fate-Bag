from pathlib import Path

import pytest
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication, QListWidgetItem

from src.core.models.enums import TokenFrontType, TokenShape, TokenState
from src.core.models.token import Token
from src.gui_pyqt.controllers.main_controller import MainController
from src.gui_pyqt.scene.token_graphics_item import TokenGraphicsItem
from src.gui_pyqt.views.main_window import MainWindow


def _ensure_offscreen() -> None:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


_ensure_offscreen()


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def window(tmp_path, qapp):
    controller = MainController(base_dir=Path(tmp_path) / "gui-runtime", deterministic_mode=True)
    main_window = MainWindow(controller=controller)
    yield main_window
    main_window.close()


def _create_test_image(path: Path, color: tuple[int, int, int]) -> str:
    image = QImage(40, 40, QImage.Format.Format_ARGB32)
    image.fill(QColor(*color))
    image.save(str(path))
    return str(path)


def test_release1_scene_renders_session_using_core_coordinates(window):

    # GIVEN
    print("\n[GIVEN] finestra tecnica con controllo scena")

    # ACT
    window._on_load_tokens()
    window._on_create_session()

    entries = window.controller.scene_entries()
    scene_items = window.table_scene.token_items()

    # EXPECTED
    print("[EXPECTED] scena contiene un item per ogni token in sessione")
    print(f"[ACTUAL] entries={len(entries)} scene_items={len(scene_items)}")
    assert len(entries) == len(scene_items)

    # EXPECTED
    print("[EXPECTED] coordinate derivate dal core non sono tutte uguali")
    positions = [
        (round(table_token.x, 3), round(table_token.y, 3))
        for _, table_token in entries
    ]
    print(f"[ACTUAL] pos_uniche={len(set(positions))}")
    assert len(set(positions)) > 1


def test_release1_scene_click_flip_updates_state(window):

    window._on_load_tokens()
    window._on_create_session()

    scene_items = window.table_scene.token_items()
    first_token_id = next(iter(scene_items.keys()))

    # GIVEN
    print("\n[GIVEN] token inizialmente FACE_DOWN")

    # ACT
    window._on_scene_token_flip(first_token_id)

    # EXPECTED
    matching_rows = []
    for i in range(window.token_list.count()):
        row: QListWidgetItem = window.token_list.item(i)
        row_token_id = row.data(0x0100)
        if row_token_id == first_token_id:
            matching_rows.append(row.text())

    print("[EXPECTED] riga token mostra stato FACE_UP dopo flip")
    print(f"[ACTUAL] rows={matching_rows}")
    assert matching_rows
    assert any("FACE_UP" in row_text for row_text in matching_rows)


def test_release1_shuffle_moves_tokens_in_scene(window):
    window._on_load_tokens()
    window._on_create_session()

    before_map = {
        str(token.id): (round(table_token.x, 3), round(table_token.y, 3))
        for token, table_token in window.controller.scene_entries()
    }

    window._on_shuffle()

    after_map = {
        str(token.id): (round(table_token.x, 3), round(table_token.y, 3))
        for token, table_token in window.controller.scene_entries()
    }

    print("\n[GIVEN] sessione avviata con coordinate core")
    print("[EXPECTED] shuffle cambia posizione ad almeno un token")

    moved_count = sum(1 for token_id in before_map if before_map[token_id] != after_map[token_id])
    print(f"[ACTUAL] moved_count={moved_count}")

    assert moved_count > 0
    assert sorted(before_map.values()) == sorted(after_map.values())


def test_release1_graphics_item_supports_shapes_and_front_back(tmp_path):
    back_path = _create_test_image(tmp_path / "back.png", (40, 60, 90))
    front_image_path = _create_test_image(tmp_path / "front.png", (200, 200, 60))

    token_text = Token(
        name="TextToken",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value="TXT",
        back_value=back_path,
    )
    token_image = Token(
        name="ImageToken",
        shape=TokenShape.HEXAGON,
        front_type=TokenFrontType.IMAGE,
        front_value=front_image_path,
        back_value=back_path,
    )

    from src.core.models.table_token import TableToken

    table_down = TableToken(token_id=token_text.id, state=TokenState.FACE_DOWN, x=0.0, y=0.0)
    table_up = TableToken(token_id=token_image.id, state=TokenState.FACE_UP, x=0.0, y=0.0)

    text_item = TokenGraphicsItem(token=token_text, table_token=table_down)
    image_item = TokenGraphicsItem(token=token_image, table_token=table_up)

    print("\n[GIVEN] item grafici con circle/text e hexagon/image")
    print("[EXPECTED] item selezionabili e bounding rect valido")
    assert text_item.flags() & text_item.GraphicsItemFlag.ItemIsSelectable
    assert image_item.flags() & image_item.GraphicsItemFlag.ItemIsSelectable
    assert text_item.boundingRect().width() > 0
    assert image_item.boundingRect().height() > 0
