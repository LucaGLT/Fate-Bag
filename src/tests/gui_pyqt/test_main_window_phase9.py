import os
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.core.models.enums import TokenFrontType, TokenShape
from src.gui_pyqt.controllers.main_controller import MainController
from src.gui_pyqt.views.main_window import MainWindow

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _debug_case(title, given, expected, actual):
    print(f"\n[CASE] {title}")
    print(f"  GIVEN    : {given}")
    print(f"  EXPECTED : {expected}")
    print(f"  ACTUAL   : {actual}")


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


def test_main_window_has_required_controls(window):
    controls = {
        "load_tokens_btn": window.load_tokens_btn.text(),
        "create_selected_session_btn": window.create_selected_session_btn.text(),
        "new_token_btn": window.new_token_btn.text(),
        "delete_token_btn": window.delete_token_btn.text(),
        "reinsert_bag_btn": window.reinsert_bag_btn.text(),
        "select_all_btn": window.select_all_btn.text(),
        "deselect_all_btn": window.deselect_all_btn.text(),
        "draw_one_btn": window.draw_one_btn.text(),
        "draw_all_btn": window.draw_all_btn.text(),
        "draw_n_btn": window.draw_n_btn.text(),
        "shuffle_btn": window.shuffle_btn.text(),
        "sort_btn": window.sort_btn.text(),
        "front_img_upload_btn": window.front_img_upload_btn.text(),
        "front_img_delete_btn": window.front_img_delete_btn.text(),
        "back_img_upload_btn": window.back_img_upload_btn.text(),
        "back_img_delete_btn": window.back_img_delete_btn.text(),
        "reset_btn": window.reset_btn.text(),
    }

    _debug_case(
        "MainWindow controls",
        {"window_title": window.windowTitle()},
        {
            "required_controls": [
                "Carica Token",
                "Inserisci in Bag",
                "(icona add token)",
                "(icona delete token)",
                "Rimetti in Bag",
                "(icona seleziona tutto)",
                "(icona deseleziona tutto)",
                "Pesca 1",
                "Pesca Tutte",
                "Pesca N",
                "Shuffle",
                "Sort",
                "Front-Img Upload",
                "Front-Img Delete",
                "Back-Img Upload",
                "Back-Img Delete",
                "Svuota Bag",
            ]
        },
        controls,
    )

    assert controls["load_tokens_btn"] == "Carica Token"
    assert controls["create_selected_session_btn"] == "Inserisci in Bag"
    assert controls["new_token_btn"] == ""
    assert controls["delete_token_btn"] == ""
    assert window.new_token_btn.toolTip() == "New Token (1)"
    assert window.delete_token_btn.toolTip() == "Delete Token selezionati"
    assert controls["reinsert_bag_btn"] == "Rimetti in Bag"
    assert controls["select_all_btn"] == ""
    assert controls["deselect_all_btn"] == ""
    assert window.select_all_btn.toolTip() == "Seleziona Tutto"
    assert window.deselect_all_btn.toolTip() == "Deseleziona Tutto"
    assert controls["draw_one_btn"] == "Pesca 1"
    assert controls["draw_all_btn"] == "Pesca Tutte"
    assert controls["draw_n_btn"] == "Pesca N"
    assert controls["shuffle_btn"] == "Shuffle"
    assert controls["sort_btn"] == "Sort"
    assert controls["front_img_upload_btn"] == "Front-Img Upload"
    assert controls["front_img_delete_btn"] == "Front-Img Delete"
    assert controls["back_img_upload_btn"] == "Back-Img Upload"
    assert controls["back_img_delete_btn"] == "Back-Img Delete"
    assert controls["reset_btn"] == "Svuota Bag"


def test_gui_flow_load_create_draw_reveal_hide_reset(window):
    window._on_load_tokens()
    after_load_status = window.status_label.text()
    loaded_count = window.token_list.count()

    window._on_select_all_tokens()
    after_select_all_status = window.status_label.text()

    # Keep one deselected to verify list state before bag insertion.
    window.token_list.item(2).setCheckState(Qt.CheckState.Unchecked)

    window._on_create_session_from_selection()
    after_create_selected_status = window.status_label.text()
    rows_after_create_selected = [window.token_list.item(i).text() for i in range(window.token_list.count())]

    session_rows_after_create = list(rows_after_create_selected)

    window._on_draw_one()
    after_draw_one_status = window.status_label.text()

    window.draw_n_spin.setValue(2)
    window._on_draw_n()
    after_draw_n_status = window.status_label.text()

    window._on_draw_all()
    after_draw_all_status = window.status_label.text()

    window._on_shuffle()
    after_shuffle_status = window.status_label.text()

    window._on_reveal_all()
    rows_after_reveal = [window.token_list.item(i).text() for i in range(window.token_list.count())]

    window._on_hide_all()
    rows_after_hide = [window.token_list.item(i).text() for i in range(window.token_list.count())]

    window._on_reset()
    rows_after_reset = [window.token_list.item(i).text() for i in range(window.token_list.count())]

    _debug_case(
        "GUI minimum technical flow",
        {"draw_n": 2},
        {
            "load_ok": True,
            "select_all_ok": True,
            "create_selected_ok": True,
            "deselected_visible": True,
            "rows_count": loaded_count,
            "shuffle_ok": True,
            "reveal_has_face_up": True,
            "hide_has_face_down": True,
            "bag_empty_after_clear": True,
        },
        {
            "after_load_status": after_load_status,
            "after_select_all_status": after_select_all_status,
            "after_create_selected_status": after_create_selected_status,
            "rows_after_create_selected": rows_after_create_selected,
            "after_draw_one_status": after_draw_one_status,
            "after_draw_all_status": after_draw_all_status,
            "after_draw_n_status": after_draw_n_status,
            "after_shuffle_status": after_shuffle_status,
            "rows_after_create": session_rows_after_create,
            "rows_after_reveal": rows_after_reveal,
            "rows_after_hide": rows_after_hide,
            "rows_after_reset": rows_after_reset,
        },
    )

    assert after_load_status.startswith("Token caricati")
    assert after_select_all_status.startswith("Tutti i token selezionati")
    assert after_create_selected_status.startswith("Inseriti in Bag")
    assert any("Deselezionato" in row for row in rows_after_create_selected)
    assert "Pesca 1" in after_draw_one_status
    assert "Pesca Tutte" in after_draw_all_status
    assert "Pesca N" in after_draw_n_status
    assert after_shuffle_status.startswith("Shuffle")
    assert len(session_rows_after_create) == loaded_count
    assert any("FACE_UP" in row for row in rows_after_reveal)
    assert all(("FACE_DOWN" in row) or ("Deselezionato" in row) for row in rows_after_hide)
    assert all("Deselezionato" in row for row in rows_after_reset)


def test_create_session_from_selection_requires_at_least_one_token(window):
    window._on_load_tokens()
    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    window._on_create_session_from_selection()
    status = window.status_label.text()

    _debug_case(
        "Create session from selection validates empty selection",
        {"selected_token_count": 0},
        {"status_starts_with": "Errore create session da selezione"},
        {"status": status},
    )

    assert status.startswith("Errore create session da selezione")


def test_load_tokens_ignores_clicked_bool_argument(window):
    window._on_load_tokens(False)
    status = window.status_label.text()

    _debug_case(
        "Load tokens ignores clicked(bool) argument",
        {"slot_argument": False},
        {"status_starts_with": "Token caricati"},
        {"status": status},
    )

    assert status.startswith("Token caricati")


def test_reinsert_bag_restores_previous_inserted_selection(window):
    window._on_load_tokens()

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    window.token_list.item(0).setCheckState(Qt.CheckState.Checked)
    window.token_list.item(1).setCheckState(Qt.CheckState.Checked)
    window.token_list.item(2).setCheckState(Qt.CheckState.Checked)

    window._on_create_session_from_selection()
    first_inserted_ids = {
        str(token.id)
        for token, _ in window.controller.scene_entries()
    }

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)
    window.token_list.item(5).setCheckState(Qt.CheckState.Checked)

    window._on_reinsert_bag()

    checked_ids = {
        window.token_list.item(i).data(Qt.ItemDataRole.UserRole)
        for i in range(window.token_list.count())
        if window.token_list.item(i).checkState() == Qt.CheckState.Checked
    }
    reinserted_ids = {
        str(token.id)
        for token, _ in window.controller.scene_entries()
    }

    _debug_case(
        "Rimetti in Bag restores previous inserted set",
        {"initial_inserted_count": 3},
        {
            "status_starts_with": "Rimessi in Bag",
            "checked_ids_equal_first_inserted": True,
            "session_ids_equal_first_inserted": True,
        },
        {
            "status": window.status_label.text(),
            "first_inserted_ids": sorted(first_inserted_ids),
            "checked_ids": sorted(checked_ids),
            "reinserted_ids": sorted(reinserted_ids),
        },
    )

    assert window.status_label.text().startswith("Rimessi in Bag")
    assert checked_ids == first_inserted_ids
    assert reinserted_ids == first_inserted_ids


def test_draw_n_handles_invalid_request(window):
    window._on_load_tokens()
    window._on_select_all_tokens()
    window._on_create_session_from_selection()

    window.draw_n_spin.setValue(99)
    window._on_draw_n()

    status = window.status_label.text()

    _debug_case(
        "GUI handles draw N invalid request",
        {"requested_count": 99, "available_tokens": 20},
        {"status_starts_with": "Errore draw N"},
        {"status": status},
    )

    assert status.startswith("Errore draw N")


def test_sort_places_face_up_before_face_down(window):
    window._on_load_tokens()
    window._on_select_all_tokens()
    window._on_create_session_from_selection()

    window.draw_n_spin.setValue(3)
    window._on_draw_n()
    window._on_sort()

    statuses = []
    for i in range(window.token_list.count()):
        text = window.token_list.item(i).text()
        if "|" in text:
            parts = [part.strip() for part in text.split("|")]
            if len(parts) >= 2:
                statuses.append(parts[1])

    first_face_down_index = next((i for i, status in enumerate(statuses) if status == "FACE_DOWN"), None)
    first_face_up_index = next((i for i, status in enumerate(statuses) if status == "FACE_UP"), None)

    _debug_case(
        "Sort places FACE_UP before FACE_DOWN",
        {"draw_n": 3},
        {
            "status_starts_with": "Sort eseguito",
            "first_face_up_before_first_face_down": True,
        },
        {
            "status": window.status_label.text(),
            "first_face_up_index": first_face_up_index,
            "first_face_down_index": first_face_down_index,
        },
    )

    assert window.status_label.text().startswith("Sort eseguito")
    assert first_face_up_index is not None
    assert first_face_down_index is not None
    assert first_face_up_index < first_face_down_index


def test_upload_front_and_back_images_to_selected_tokens(window, tmp_path):
    window._on_load_tokens()

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    window.token_list.item(0).setCheckState(Qt.CheckState.Checked)
    window.token_list.item(1).setCheckState(Qt.CheckState.Checked)

    selected_ids = []
    for index in [0, 1]:
        token_id = window.token_list.item(index).data(Qt.ItemDataRole.UserRole)
        from uuid import UUID

        selected_ids.append(UUID(token_id))

    not_selected_id = None
    if window.token_list.count() >= 3:
        from uuid import UUID

        not_selected_id = UUID(window.token_list.item(2).data(Qt.ItemDataRole.UserRole))

    front_path = tmp_path / "front_upload.png"
    back_path = tmp_path / "back_upload.png"
    front_path.write_bytes(b"front-image")
    back_path.write_bytes(b"back-image")

    window._on_front_img_upload(str(front_path))
    after_front_status = window.status_label.text()

    window._on_back_img_upload(str(back_path))
    after_back_status = window.status_label.text()

    selected_tokens = [window.controller._tokens_by_id[token_id] for token_id in selected_ids]

    _debug_case(
        "Front/Back image upload applies to selected tokens",
        {
            "selected_count": 2,
            "front_path": str(front_path),
            "back_path": str(back_path),
        },
        {
            "front_status_starts_with": "Front image applicata",
            "back_status_starts_with": "Back image applicata",
            "selected_front_type": "TEXT_IMAGE",
            "selected_front_value": str(front_path),
            "selected_back_value": str(back_path),
        },
        {
            "after_front_status": after_front_status,
            "after_back_status": after_back_status,
            "selected_tokens": [
                {
                    "name": token.name,
                    "front_type": token.front_type.value,
                    "front_value": token.front_value,
                    "back_value": token.back_value,
                }
                for token in selected_tokens
            ],
        },
    )

    assert after_front_status.startswith("Front image applicata")
    assert after_back_status.startswith("Back image applicata")
    assert all(token.front_type == TokenFrontType.TEXT_IMAGE for token in selected_tokens)
    assert all(token.front_value == str(front_path) for token in selected_tokens)
    assert all(token.back_value == str(back_path) for token in selected_tokens)
    assert all(str(token.metadata.get("front_text", "")).strip() for token in selected_tokens)

    if not_selected_id is not None:
        not_selected = window.controller._tokens_by_id[not_selected_id]
        assert not_selected.front_value != str(front_path)


def test_delete_front_and_back_images_for_selected_tokens(window, tmp_path):
    window._on_load_tokens()

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    window.token_list.item(0).setCheckState(Qt.CheckState.Checked)

    token_id_raw = window.token_list.item(0).data(Qt.ItemDataRole.UserRole)
    from uuid import UUID

    token_uuid = UUID(token_id_raw)

    front_path = tmp_path / "front_delete_case.png"
    back_path = tmp_path / "back_delete_case.png"
    front_path.write_bytes(b"front-image")
    back_path.write_bytes(b"back-image")

    window._on_front_img_upload(str(front_path))
    window._on_back_img_upload(str(back_path))

    window._on_front_img_delete()
    front_delete_status = window.status_label.text()

    window._on_back_img_delete()
    back_delete_status = window.status_label.text()

    token = window.controller._tokens_by_id[token_uuid]

    _debug_case(
        "Delete front/back image for selected token",
        {"selected_count": 1},
        {
            "front_delete_status": "Front image rimossa",
            "back_delete_status": "Back image rimossa",
            "front_type_after_delete": "TEXT",
        },
        {
            "front_delete_status": front_delete_status,
            "back_delete_status": back_delete_status,
            "token": {
                "front_type": token.front_type.value,
                "front_value": token.front_value,
                "back_value": token.back_value,
            },
        },
    )

    assert front_delete_status.startswith("Front image rimossa")
    assert back_delete_status.startswith("Back image rimossa")
    assert token.front_type == TokenFrontType.TEXT
    assert token.back_value.endswith("assets\\back.png") or token.back_value.endswith("assets/back.png")


def test_front_text_edit_updates_text_in_text_and_text_image_modes(window, tmp_path):
    window._on_load_tokens()

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    window.token_list.item(0).setCheckState(Qt.CheckState.Checked)
    token0_id = window.token_list.item(0).data(Qt.ItemDataRole.UserRole)
    from uuid import UUID

    token0_uuid = UUID(token0_id)

    window._on_front_text_edit("Nuovo Testo Solo")
    token0 = window.controller._tokens_by_id[token0_uuid]

    assert token0.front_type == TokenFrontType.TEXT
    assert token0.front_value == "Nuovo Testo Solo"

    front_path = tmp_path / "front_for_text_image.png"
    front_path.write_bytes(b"front-image")

    window._on_front_img_upload(str(front_path))
    window._on_front_text_edit("Overlay Testo")

    token0_after = window.controller._tokens_by_id[token0_uuid]

    _debug_case(
        "Front text edit supports TEXT and TEXT_IMAGE",
        {
            "selected_count": 1,
            "front_image": str(front_path),
            "new_text": "Overlay Testo",
        },
        {
            "status_starts_with": "Front text aggiornato",
            "front_type": "TEXT_IMAGE",
            "metadata.front_text": "Overlay Testo",
        },
        {
            "status": window.status_label.text(),
            "front_type": token0_after.front_type.value,
            "front_value": token0_after.front_value,
            "metadata": token0_after.metadata,
        },
    )

    assert window.status_label.text().startswith("Front text aggiornato")
    assert token0_after.front_type == TokenFrontType.TEXT_IMAGE
    assert token0_after.front_value == str(front_path)
    assert token0_after.metadata.get("front_text") == "Overlay Testo"


def test_front_text_edit_directly_from_checkbox_list(window):
    window._on_load_tokens()

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    # Token 0 starts unchecked on purpose to verify auto-select on double click.
    window.token_list.item(1).setCheckState(Qt.CheckState.Checked)

    from uuid import UUID

    token0_id = UUID(window.token_list.item(0).data(Qt.ItemDataRole.UserRole))
    token1_id = UUID(window.token_list.item(1).data(Qt.ItemDataRole.UserRole))
    token2_id = UUID(window.token_list.item(2).data(Qt.ItemDataRole.UserRole))

    clicked_item = window.token_list.item(0)
    window._on_token_list_item_double_clicked(clicked_item, text="Testo Da Lista")

    token0 = window.controller._tokens_by_id[token0_id]
    token1 = window.controller._tokens_by_id[token1_id]
    token2 = window.controller._tokens_by_id[token2_id]

    _debug_case(
        "Front text edited directly from checkbox list",
        {
            "checked_tokens_before": [str(token1_id)],
            "double_clicked_row": str(token0_id),
            "new_text": "Testo Da Lista",
        },
        {
            "status_starts_with": "Token aggiornati da lista",
            "double_clicked_auto_selected": True,
            "checked_tokens_updated": True,
            "unchecked_token_unchanged": True,
        },
        {
            "status": window.status_label.text(),
            "token0_checked": window.token_list.item(0).checkState() == Qt.CheckState.Checked,
            "token0": {
                "front_type": token0.front_type.value,
                "front_value": token0.front_value,
                "metadata": token0.metadata,
            },
            "token1": {
                "front_type": token1.front_type.value,
                "front_value": token1.front_value,
                "metadata": token1.metadata,
            },
            "token2": {
                "front_type": token2.front_type.value,
                "front_value": token2.front_value,
                "metadata": token2.metadata,
            },
        },
    )

    assert window.status_label.text().startswith("Token aggiornati da lista")
    assert window.token_list.item(0).checkState() == Qt.CheckState.Checked
    assert (
        token0.front_value == "Testo Da Lista"
        or token0.metadata.get("front_text") == "Testo Da Lista"
    )
    assert (
        token1.front_value == "Testo Da Lista"
        or token1.metadata.get("front_text") == "Testo Da Lista"
    )
    assert (
        token2.front_value != "Testo Da Lista"
        and token2.metadata.get("front_text") != "Testo Da Lista"
    )


def test_token_popup_edit_updates_name_tags_shape_for_selected_tokens(window):
    window._on_load_tokens()

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    window.token_list.item(0).setCheckState(Qt.CheckState.Checked)
    window.token_list.item(1).setCheckState(Qt.CheckState.Checked)

    from uuid import UUID

    token0_id = UUID(window.token_list.item(0).data(Qt.ItemDataRole.UserRole))
    token1_id = UUID(window.token_list.item(1).data(Qt.ItemDataRole.UserRole))
    token2_id = UUID(window.token_list.item(2).data(Qt.ItemDataRole.UserRole))

    clicked_item = window.token_list.item(0)
    window._on_token_list_item_double_clicked(
        clicked_item,
        text="Token Multi Edit",
        tags_text="alpha; beta, gamma",
        shape=TokenShape.OCTAGON,
    )

    token0 = window.controller._tokens_by_id[token0_id]
    token1 = window.controller._tokens_by_id[token1_id]
    token2 = window.controller._tokens_by_id[token2_id]

    _debug_case(
        "Popup token edit updates selected tokens",
        {
            "selected_count": 2,
            "name": "Token Multi Edit",
            "tags": ["alpha", "beta", "gamma"],
            "shape": TokenShape.OCTAGON.value,
        },
        {
            "status_starts_with": "Token aggiornati da lista",
            "token0_updated": True,
            "token1_updated": True,
            "token2_unchanged": True,
        },
        {
            "status": window.status_label.text(),
            "token0": {
                "name": token0.name,
                "tags": token0.tags,
                "shape": token0.shape.value,
            },
            "token1": {
                "name": token1.name,
                "tags": token1.tags,
                "shape": token1.shape.value,
            },
            "token2": {
                "name": token2.name,
                "tags": token2.tags,
                "shape": token2.shape.value,
            },
        },
    )

    assert window.status_label.text().startswith("Token aggiornati da lista")
    assert token0.name == "Token Multi Edit"
    assert token1.name == "Token Multi Edit"
    assert token0.tags == ["alpha", "beta", "gamma"]
    assert token1.tags == ["alpha", "beta", "gamma"]
    assert token0.shape == TokenShape.OCTAGON
    assert token1.shape == TokenShape.OCTAGON
    assert token2.name != "Token Multi Edit"


def test_select_and_deselect_all_buttons(window):
    window._on_load_tokens()

    window._on_select_all_tokens()
    all_checked = all(
        window.token_list.item(i).checkState() == Qt.CheckState.Checked
        for i in range(window.token_list.count())
    )

    window._on_deselect_all_tokens()
    all_unchecked = all(
        window.token_list.item(i).checkState() == Qt.CheckState.Unchecked
        for i in range(window.token_list.count())
    )

    _debug_case(
        "Select/Deselect all buttons",
        {"token_count": window.token_list.count()},
        {"all_checked": True, "all_unchecked": True},
        {"all_checked": all_checked, "all_unchecked": all_unchecked},
    )

    assert all_checked
    assert all_unchecked


def test_new_and_delete_token_buttons(window):
    window._on_load_tokens()
    initial_count = window.token_list.count()

    window._on_new_token()
    after_new_count = window.token_list.count()

    assert after_new_count == initial_count + 1
    assert window.status_label.text().startswith("Nuovo token creato")

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    last_index = window.token_list.count() - 1
    window.token_list.item(last_index).setCheckState(Qt.CheckState.Checked)
    window._on_delete_selected_tokens()

    after_delete_count = window.token_list.count()
    _debug_case(
        "New/Delete token buttons",
        {"initial_count": initial_count},
        {
            "after_new_count": initial_count + 1,
            "after_delete_count": initial_count,
            "status_starts_with": "Token eliminati",
        },
        {
            "after_new_count": after_new_count,
            "after_delete_count": after_delete_count,
            "status": window.status_label.text(),
        },
    )

    assert after_delete_count == initial_count
    assert window.status_label.text().startswith("Token eliminati")


def test_checkbox_selection_updates_scene_highlight(window):
    window._on_load_tokens()

    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    # Create session with first three tokens so they exist on the table scene.
    window.token_list.item(0).setCheckState(Qt.CheckState.Checked)
    window.token_list.item(1).setCheckState(Qt.CheckState.Checked)
    window.token_list.item(2).setCheckState(Qt.CheckState.Checked)
    window._on_create_session_from_selection()

    token_id_0 = window.token_list.item(0).data(Qt.ItemDataRole.UserRole)
    token_id_1 = window.token_list.item(1).data(Qt.ItemDataRole.UserRole)

    scene_items = window.table_scene.token_items()
    item0 = scene_items[token_id_0]
    item1 = scene_items[token_id_1]

    # Uncheck all, then select one and verify only that one is highlighted.
    for index in range(window.token_list.count()):
        window.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)

    row0 = None
    row1 = None
    for i in range(window.token_list.count()):
        row = window.token_list.item(i)
        if row.data(Qt.ItemDataRole.UserRole) == token_id_0:
            row0 = row
        if row.data(Qt.ItemDataRole.UserRole) == token_id_1:
            row1 = row

    assert row0 is not None
    assert row1 is not None

    row0.setCheckState(Qt.CheckState.Checked)

    _debug_case(
        "Checkbox selection controls scene highlight",
        {"checked_token": token_id_0},
        {"item0_selected": True, "item1_selected": False},
        {"item0_selected": item0.isSelected(), "item1_selected": item1.isSelected()},
    )

    assert item0.isSelected() is True
    assert item1.isSelected() is False

    row0.setCheckState(Qt.CheckState.Unchecked)

    _debug_case(
        "Uncheck removes scene highlight",
        {"unchecked_token": token_id_0},
        {"item0_selected": False},
        {"item0_selected": item0.isSelected()},
    )

    assert item0.isSelected() is False
