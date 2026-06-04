from pathlib import Path
import json

import pytest
from PyQt6.QtCore import Qt
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


def test_release1_scene_single_click_selects_checkbox(window):
    window._on_load_tokens()
    window._on_create_session()

    target_token_id = next(iter(window.table_scene.token_items().keys()))

    target_row = None
    for i in range(window.token_list.count()):
        row = window.token_list.item(i)
        if row.data(0x0100) == target_token_id:
            target_row = row
        row.setCheckState(Qt.CheckState.Unchecked)

    assert target_row is not None

    window._on_scene_token_selected(target_token_id)

    print("\n[GIVEN] token in lista deselezionato manualmente")
    print("[EXPECTED] click singolo su token scena selezione esclusiva checkbox")
    assert target_row.checkState() == Qt.CheckState.Checked
    checked_count = sum(
        1
        for i in range(window.token_list.count())
        if window.token_list.item(i).checkState() == Qt.CheckState.Checked
    )
    assert checked_count == 1


def test_release1_scene_double_click_selects_and_flips(window):
    window._on_load_tokens()
    window._on_create_session()

    target_token_id = next(iter(window.table_scene.token_items().keys()))

    target_row = None
    for i in range(window.token_list.count()):
        row = window.token_list.item(i)
        if row.data(0x0100) == target_token_id:
            target_row = row
        row.setCheckState(Qt.CheckState.Unchecked)

    assert target_row is not None
    window._on_scene_token_selected(target_token_id)
    window._on_scene_token_flip(target_token_id)

    refreshed_row = None
    for i in range(window.token_list.count()):
        row = window.token_list.item(i)
        if row.data(0x0100) == target_token_id:
            refreshed_row = row
            break

    assert refreshed_row is not None

    print("\n[GIVEN] doppio click simulato con select + flip")
    print("[EXPECTED] checkbox selezionata e stato token FACE_UP")
    assert refreshed_row.checkState() == Qt.CheckState.Checked
    assert "FACE_UP" in refreshed_row.text()
    checked_count = sum(
        1
        for i in range(window.token_list.count())
        if window.token_list.item(i).checkState() == Qt.CheckState.Checked
    )
    assert checked_count == 1


def test_release1_scene_drag_drop_moves_token_and_selects_checkbox(window):
    window._on_load_tokens()
    window._on_create_session()

    entries_before = {
        str(token.id): (table_token.x, table_token.y)
        for token, table_token in window.controller.scene_entries()
    }

    target_token_id = next(iter(entries_before.keys()))

    target_row = None
    for i in range(window.token_list.count()):
        row = window.token_list.item(i)
        if row.data(0x0100) == target_token_id:
            target_row = row
        row.setCheckState(Qt.CheckState.Unchecked)

    assert target_row is not None
    window._on_scene_token_dragged(target_token_id, 12.5, 33.3)

    entries_after = {
        str(token.id): (table_token.x, table_token.y)
        for token, table_token in window.controller.scene_entries()
    }

    print("\n[GIVEN] drag&drop token su nuova posizione core")
    print("[EXPECTED] checkbox selezionata e coordinate token aggiornate")
    assert target_row.checkState() == Qt.CheckState.Checked
    checked_count = sum(
        1
        for i in range(window.token_list.count())
        if window.token_list.item(i).checkState() == Qt.CheckState.Checked
    )
    assert checked_count == 1
    assert entries_before[target_token_id] != entries_after[target_token_id]
    assert entries_after[target_token_id] == (12.5, 33.3)


def test_release1_scene_grid_tracks_visible_table_area_on_resize(window):
    window._on_load_tokens()
    window._on_create_session()

    initial_rect = window.table_scene.sceneRect()
    initial_items = window.table_scene.token_items()
    first_token_id = next(iter(initial_items.keys()))
    initial_pos = initial_items[first_token_id].pos()

    window.table_scene.update_viewport_rect(
        initial_rect.width() - 180.0,
        initial_rect.height() - 120.0,
    )
    QApplication.processEvents()

    resized_rect = window.table_scene.sceneRect()
    resized_items = window.table_scene.token_items()
    resized_pos = resized_items[first_token_id].pos()

    print("\n[GIVEN] tavolo ridimensionato con finestra più piccola")
    print("[EXPECTED] sceneRect segue la viewport reale e token si riposizionano")

    assert resized_rect.width() < initial_rect.width()
    assert resized_rect.height() < initial_rect.height()
    assert (round(resized_pos.x(), 2), round(resized_pos.y(), 2)) != (
        round(initial_pos.x(), 2),
        round(initial_pos.y(), 2),
    )


def test_release1_can_hide_and_show_checkbox_list(window):
    sizes_before = window.content_splitter.sizes()
    assert len(sizes_before) == 2
    assert sizes_before[0] > 0

    window._toggle_token_list_visibility()
    QApplication.processEvents()

    sizes_hidden = window.content_splitter.sizes()
    print("\n[GIVEN] toggle lista checkbox")
    print("[EXPECTED] primo toggle nasconde lista")
    assert sizes_hidden[0] == 0

    window._toggle_token_list_visibility()
    QApplication.processEvents()

    sizes_shown = window.content_splitter.sizes()
    print("[EXPECTED] secondo toggle ripristina lista")
    assert sizes_shown[0] > 0


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


def test_release1_sort_places_face_up_above_face_down(window):
    window._on_load_tokens()
    window._on_select_all_tokens()
    window._on_create_session_from_selection()

    window.draw_n_spin.setValue(3)
    window._on_draw_n()
    window._on_sort()

    entries = window.controller.scene_entries()
    face_up_y = [table_token.y for _, table_token in entries if table_token.state == TokenState.FACE_UP]
    face_down_y = [table_token.y for _, table_token in entries if table_token.state == TokenState.FACE_DOWN]

    print("\n[GIVEN] sort eseguito dopo alcuni draw")
    print("[EXPECTED] token FACE_UP in media più in alto dei FACE_DOWN")
    assert face_up_y
    assert face_down_y
    assert max(face_up_y) <= min(face_down_y)


def test_release1_scene_multi_selection_updates_checkbox_list(window):
    window._on_load_tokens()
    window._on_create_session()

    for i in range(window.token_list.count()):
        window.token_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    scene_ids = list(window.table_scene.token_items().keys())
    assert len(scene_ids) >= 2
    selected_ids = {scene_ids[0], scene_ids[1]}

    window.table_scene.set_selected_token_ids(selected_ids)

    checked_ids = {
        window.token_list.item(i).data(0x0100)
        for i in range(window.token_list.count())
        if window.token_list.item(i).checkState() == Qt.CheckState.Checked
    }

    print("\n[GIVEN] selezione multipla in scena simulata (come Ctrl+click)")
    print("[EXPECTED] checkbox lista allineate con stessi token selezionati")
    assert checked_ids == selected_ids


def test_release1_checkbox_tree_groups_tokens_by_categories(tmp_path, window):
    back_path = _create_test_image(tmp_path / "back_categories.png", (40, 60, 90))

    token_pg = Token(
        name="PG-Root",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value="PG-Root",
        back_value=back_path,
        categories=["PG"],
    )
    token_n1 = Token(
        name="Nariel-1",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value="Nariel-1",
        back_value=back_path,
        categories=["PG>Nariel"],
    )
    token_n2 = Token(
        name="Nariel-2",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value="Nariel-2",
        back_value=back_path,
        categories=["PG>Nariel"],
    )

    json_path = tmp_path / "tree_categories.json"
    json_path.write_text(
        json.dumps(
            {
                "tokens": [
                    token_pg.model_dump(mode="json"),
                    token_n1.model_dump(mode="json"),
                    token_n2.model_dump(mode="json"),
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    window._on_load_tokens(str(json_path))

    root_pg = None
    for i in range(window.token_list.topLevelItemCount()):
        node = window.token_list.topLevelItem(i)
        if node.text(0) == "PG":
            root_pg = node
            break

    print("\n[GIVEN] token con categories PG e PG>Nariel")
    print("[EXPECTED] albero con nodo PG e sotto-nodo Nariel")
    assert root_pg is not None

    nariel = None
    for i in range(root_pg.childCount()):
        child = root_pg.child(i)
        if child.text(0) == "Nariel":
            nariel = child
            break

    assert nariel is not None
    assert nariel.childCount() == 2


def test_release1_checkbox_tree_parent_check_selects_all_descendants(tmp_path, window):
    back_path = _create_test_image(tmp_path / "back_parent_check.png", (40, 60, 90))

    token_a = Token(
        name="Nariel-A",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value="Nariel-A",
        back_value=back_path,
        categories=["PG>Nariel"],
    )
    token_b = Token(
        name="Nariel-B",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value="Nariel-B",
        back_value=back_path,
        categories=["PG>Nariel"],
    )

    json_path = tmp_path / "tree_parent_select.json"
    json_path.write_text(
        json.dumps(
            {"tokens": [token_a.model_dump(mode="json"), token_b.model_dump(mode="json")]},
            indent=2,
        ),
        encoding="utf-8",
    )

    window._on_load_tokens(str(json_path))

    root_pg = None
    for i in range(window.token_list.topLevelItemCount()):
        node = window.token_list.topLevelItem(i)
        if node.text(0) == "PG":
            root_pg = node
            break
    assert root_pg is not None

    root_pg.setCheckState(0, Qt.CheckState.Checked)

    def _collect_token_leaves(node) -> list:
        leaves = []
        if node.childCount() <= 0:
            if node.data(0, Qt.ItemDataRole.UserRole):
                leaves.append(node)
            return leaves
        for idx in range(node.childCount()):
            leaves.extend(_collect_token_leaves(node.child(idx)))
        return leaves

    leaves = _collect_token_leaves(root_pg)

    print("\n[GIVEN] check sul nodo padre PG")
    print("[EXPECTED] tutti i token discendenti risultano selezionati")
    assert leaves
    assert all(leaf.checkState(0) == Qt.CheckState.Checked for leaf in leaves)


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


def test_release1_hover_tip_overlay_expands_bounding_rect(tmp_path):
    back_path = _create_test_image(tmp_path / "back_tip.png", (40, 60, 90))
    front_image_path = _create_test_image(tmp_path / "front_tip.png", (200, 200, 60))

    token = Token(
        name="TipToken",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.IMAGE,
        front_value=front_image_path,
        back_value=back_path,
        metadata={
            "front_text": "<TipToken>|Front hover text",
            "tip_text": "<Dettagli>|riga uno|riga due",
        },
    )

    from src.core.models.table_token import TableToken

    table_token = TableToken(token_id=token.id, state=TokenState.FACE_UP, x=0.0, y=0.0)
    item = TokenGraphicsItem(token=token, table_token=table_token)

    base_rect = item.boundingRect()
    item._set_hover_preview_enabled(True)
    hover_rect = item.boundingRect()

    print("\n[GIVEN] token IMAGE con front_text e tip_text in hover")
    print("[EXPECTED] hover amplia il bounding rect verso il basso per overlay tip")

    assert hover_rect.height() > base_rect.height()
    assert hover_rect.bottom() > base_rect.bottom()


def test_release1_token_graphics_item_uses_configurable_font_sizes(tmp_path):
    back_path = _create_test_image(tmp_path / "back_font.png", (40, 60, 90))
    front_image_path = _create_test_image(tmp_path / "front_font.png", (200, 200, 60))

    token = Token(
        name="FontToken",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT_IMAGE,
        front_value=front_image_path,
        back_value=back_path,
        metadata={
            "front_text": "<FontToken>|Front",
            "tip_text": "<FontToken>|Tip|Riga 2",
        },
    )

    from src.core.models.table_token import TableToken

    table_token = TableToken(token_id=token.id, state=TokenState.FACE_UP, x=0.0, y=0.0)
    item = TokenGraphicsItem(
        token=token,
        table_token=table_token,
        front_text_font_px=12,
        tip_text_font_px=14,
    )

    print("\n[GIVEN] item grafico con font size configurabili")
    print("[EXPECTED] font px salvati sull'item")
    assert item._front_text_font_px == 12
    assert item._tip_text_font_px == 14


def test_release1_title_font_is_base_plus_two():
    rich = TokenGraphicsItem._to_rich_text(
        "<Titolo>|riga",
        "#ffffff",
        title_font_px=12,
    )

    print("\n[GIVEN] front_text_font_px=10 (title font 12)")
    print("[EXPECTED] titolo tra <> renderizzato con font-size:12px")
    assert "font-size:12px" in rich


def test_release1_graphics_item_supports_all_requested_shapes(tmp_path):
    back_path = _create_test_image(tmp_path / "back_shapes.png", (20, 30, 40))

    from src.core.models.table_token import TableToken

    shapes = [
        TokenShape.CIRCLE,
        TokenShape.SQUARE,
        TokenShape.PENTAGON,
        TokenShape.EPTAGON,
        TokenShape.HEXAGON,
        TokenShape.OCTAGON,
        TokenShape.STAR,
        TokenShape.RECTANGLE_3_4,
        TokenShape.RECTANGLE_4_3,
        TokenShape.RECTANGLE_3_5,
        TokenShape.RECTANGLE_5_3,
    ]

    print("\n[GIVEN] tutte le shape richieste disponibili nel dominio")
    print("[EXPECTED] ogni shape produce un path grafico valido non vuoto")

    for shape in shapes:
        token = Token(
            name=f"Shape-{shape.value}",
            shape=shape,
            front_type=TokenFrontType.TEXT,
            front_value=shape.value,
            back_value=back_path,
        )
        table = TableToken(token_id=token.id, state=TokenState.FACE_DOWN, x=0.0, y=0.0)
        item = TokenGraphicsItem(token=token, table_token=table)

        path = item._shape_path()
        assert not path.isEmpty(), f"Shape path empty for {shape.value}"


def test_release1_hover_preview_switches_image_to_text_and_restores(tmp_path):
    back_path = _create_test_image(tmp_path / "back_hover_preview.png", (25, 35, 45))
    front_image_path = _create_test_image(tmp_path / "front_hover_preview.png", (210, 160, 90))

    token = Token(
        name="HoverName",
        shape=TokenShape.SQUARE,
        front_type=TokenFrontType.IMAGE,
        front_value=front_image_path,
        back_value=back_path,
        metadata={"front_text": "<Titolo> **Bold**|riga *2*"},
    )

    from src.core.models.table_token import TableToken

    table = TableToken(token_id=token.id, state=TokenState.FACE_UP, x=0.0, y=0.0)
    item = TokenGraphicsItem(token=token, table_token=table)

    assert item._effective_front_type() == TokenFrontType.IMAGE

    item._set_hover_preview_enabled(True)
    assert item._effective_front_type() == TokenFrontType.TEXT
    assert item._front_label_text(item._effective_front_type()) == "<Titolo> **Bold**\nriga *2*"

    item._set_hover_preview_enabled(False)
    assert item._effective_front_type() == TokenFrontType.IMAGE


def test_release1_hover_preview_keeps_text_mode_without_front_image(tmp_path):
    back_path = _create_test_image(tmp_path / "back_hover_text.png", (70, 80, 90))

    token = Token(
        name="TextOnly",
        shape=TokenShape.CIRCLE,
        front_type=TokenFrontType.TEXT,
        front_value="Solo testo",
        back_value=back_path,
    )

    from src.core.models.table_token import TableToken

    table = TableToken(token_id=token.id, state=TokenState.FACE_UP, x=0.0, y=0.0)
    item = TokenGraphicsItem(token=token, table_token=table)

    assert item._effective_front_type() == TokenFrontType.TEXT

    item._set_hover_preview_enabled(True)
    assert item._effective_front_type() == TokenFrontType.TEXT
    assert item._front_label_text(item._effective_front_type()) == "Solo testo"
