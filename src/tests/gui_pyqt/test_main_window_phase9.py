import os
from pathlib import Path

import pytest
from PyQt6.QtWidgets import QApplication

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
        "create_session_btn": window.create_session_btn.text(),
        "draw_one_btn": window.draw_one_btn.text(),
        "draw_n_btn": window.draw_n_btn.text(),
        "shuffle_btn": window.shuffle_btn.text(),
        "reveal_all_btn": window.reveal_all_btn.text(),
        "hide_all_btn": window.hide_all_btn.text(),
        "reset_btn": window.reset_btn.text(),
    }

    _debug_case(
        "MainWindow controls",
        {"window_title": window.windowTitle()},
        {
            "required_controls": [
                "Carica token",
                "Crea sessione",
                "Draw 1",
                "Draw N",
                "Shuffle",
                "Reveal all",
                "Hide all",
                "Reset",
            ]
        },
        controls,
    )

    assert controls["load_tokens_btn"] == "Carica token"
    assert controls["create_session_btn"] == "Crea sessione"
    assert controls["draw_one_btn"] == "Draw 1"
    assert controls["draw_n_btn"] == "Draw N"
    assert controls["shuffle_btn"] == "Shuffle"
    assert controls["reveal_all_btn"] == "Reveal all"
    assert controls["hide_all_btn"] == "Hide all"
    assert controls["reset_btn"] == "Reset"


def test_gui_flow_load_create_draw_reveal_hide_reset(window):
    window._on_load_tokens()
    after_load_status = window.status_label.text()

    window._on_create_session()
    after_create_status = window.status_label.text()
    session_rows_after_create = [window.token_list.item(i).text() for i in range(window.token_list.count())]

    window._on_draw_one()
    after_draw_one_status = window.status_label.text()

    window.draw_n_spin.setValue(2)
    window._on_draw_n()
    after_draw_n_status = window.status_label.text()

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
            "session_created": True,
            "rows_count": 3,
            "shuffle_ok": True,
            "reveal_has_face_up": True,
            "hide_has_face_down": True,
            "reset_has_face_down": True,
        },
        {
            "after_load_status": after_load_status,
            "after_create_status": after_create_status,
            "after_draw_one_status": after_draw_one_status,
            "after_draw_n_status": after_draw_n_status,
            "after_shuffle_status": after_shuffle_status,
            "rows_after_create": session_rows_after_create,
            "rows_after_reveal": rows_after_reveal,
            "rows_after_hide": rows_after_hide,
            "rows_after_reset": rows_after_reset,
        },
    )

    assert after_load_status.startswith("Token caricati")
    assert after_create_status.startswith("Sessione creata")
    assert "Draw 1" in after_draw_one_status
    assert "Draw N" in after_draw_n_status
    assert after_shuffle_status.startswith("Shuffle")
    assert len(session_rows_after_create) == 3
    assert any("FACE_UP" in row for row in rows_after_reveal)
    assert all("FACE_DOWN" in row for row in rows_after_hide)
    assert all("FACE_DOWN" in row for row in rows_after_reset)


def test_draw_n_handles_invalid_request(window):
    window._on_load_tokens()
    window._on_create_session()

    window.draw_n_spin.setValue(99)
    window._on_draw_n()

    status = window.status_label.text()

    _debug_case(
        "GUI handles draw N invalid request",
        {"requested_count": 99, "available_tokens": 3},
        {"status_starts_with": "Errore draw N"},
        {"status": status},
    )

    assert status.startswith("Errore draw N")
