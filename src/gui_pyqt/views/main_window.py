from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

from src.gui_pyqt.controllers.main_controller import MainController
from src.gui_pyqt.scene.token_table_scene import TokenTableScene


class MainWindow(QMainWindow):
    def __init__(self, controller: MainController | None = None) -> None:
        super().__init__()
        self.controller = controller or MainController()

        self.setWindowTitle("Fate-Bag - GUI Tecnica Minima")
        self.resize(760, 480)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        button_row = QHBoxLayout()

        self.load_tokens_btn = QPushButton("Carica token")
        self.load_tokens_btn.setObjectName("load_tokens_btn")
        button_row.addWidget(self.load_tokens_btn)

        self.create_session_btn = QPushButton("Crea sessione")
        self.create_session_btn.setObjectName("create_session_btn")
        button_row.addWidget(self.create_session_btn)

        self.create_selected_session_btn = QPushButton("Crea sessione da selezione")
        self.create_selected_session_btn.setObjectName("create_selected_session_btn")
        button_row.addWidget(self.create_selected_session_btn)

        self.draw_one_btn = QPushButton("Draw 1")
        self.draw_one_btn.setObjectName("draw_one_btn")
        button_row.addWidget(self.draw_one_btn)

        self.draw_n_spin = QSpinBox()
        self.draw_n_spin.setObjectName("draw_n_spin")
        self.draw_n_spin.setMinimum(1)
        self.draw_n_spin.setMaximum(99)
        self.draw_n_spin.setValue(2)
        button_row.addWidget(self.draw_n_spin)

        self.draw_n_btn = QPushButton("Draw N")
        self.draw_n_btn.setObjectName("draw_n_btn")
        button_row.addWidget(self.draw_n_btn)

        self.shuffle_btn = QPushButton("Shuffle")
        self.shuffle_btn.setObjectName("shuffle_btn")
        button_row.addWidget(self.shuffle_btn)

        self.sort_btn = QPushButton("Sort")
        self.sort_btn.setObjectName("sort_btn")
        button_row.addWidget(self.sort_btn)

        self.reveal_all_btn = QPushButton("Reveal all")
        self.reveal_all_btn.setObjectName("reveal_all_btn")
        button_row.addWidget(self.reveal_all_btn)

        self.hide_all_btn = QPushButton("Hide all")
        self.hide_all_btn.setObjectName("hide_all_btn")
        button_row.addWidget(self.hide_all_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("reset_btn")
        button_row.addWidget(self.reset_btn)

        layout.addLayout(button_row)

        self.status_label = QLabel("Pronto")
        self.status_label.setObjectName("status_label")
        layout.addWidget(self.status_label)

        content_row = QHBoxLayout()

        self.token_list = QListWidget()
        self.token_list.setObjectName("token_list")
        content_row.addWidget(self.token_list, 1)

        self.table_scene = TokenTableScene()
        self.table_view = QGraphicsView(self.table_scene)
        self.table_view.setObjectName("table_view")
        self.table_view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.table_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        content_row.addWidget(self.table_view, 2)

        layout.addLayout(content_row)

    def _connect_signals(self) -> None:
        self.load_tokens_btn.clicked.connect(self._on_load_tokens)
        self.create_session_btn.clicked.connect(self._on_create_session)
        self.create_selected_session_btn.clicked.connect(self._on_create_session_from_selection)
        self.draw_one_btn.clicked.connect(self._on_draw_one)
        self.draw_n_btn.clicked.connect(self._on_draw_n)
        self.shuffle_btn.clicked.connect(self._on_shuffle)
        self.sort_btn.clicked.connect(self._on_sort)
        self.reveal_all_btn.clicked.connect(self._on_reveal_all)
        self.hide_all_btn.clicked.connect(self._on_hide_all)
        self.reset_btn.clicked.connect(self._on_reset)
        self.table_scene.token_flip_requested.connect(self._on_scene_token_flip)

    def _on_load_tokens(self) -> None:
        try:
            tokens = self.controller.load_tokens()
            self.status_label.setText(f"Token caricati: {len(tokens)}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore load: {exc}")

    def _on_create_session(self) -> None:
        try:
            session = self.controller.create_session()
            self.status_label.setText(f"Sessione creata: {session.session_id}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore create session: {exc}")

    def _on_create_session_from_selection(self) -> None:
        try:
            selected_ids = list(self._checked_token_ids_from_ui())
            session = self.controller.create_session_from_selection(selected_ids)
            self.status_label.setText(f"Sessione da selezione creata: {session.session_id}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore create session da selezione: {exc}")

    def _on_draw_one(self) -> None:
        try:
            drawn = self.controller.draw_one()
            self.status_label.setText(f"Draw 1: {drawn}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore draw 1: {exc}")

    def _on_draw_n(self) -> None:
        try:
            drawn = self.controller.draw_many(self.draw_n_spin.value())
            self.status_label.setText(f"Draw N: {drawn}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore draw N: {exc}")

    def _on_shuffle(self) -> None:
        try:
            self.controller.shuffle()
            self.status_label.setText("Shuffle eseguito")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore shuffle: {exc}")

    def _on_sort(self) -> None:
        try:
            self.controller.sort_face_up_first()
            self.status_label.setText("Sort eseguito (FACE_UP -> FACE_DOWN)")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore sort: {exc}")

    def _on_reveal_all(self) -> None:
        try:
            token_ids = self.controller.reveal_all()
            self.status_label.setText(f"Reveal all: {len(token_ids)} token")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore reveal all: {exc}")

    def _on_hide_all(self) -> None:
        try:
            token_ids = self.controller.hide_all()
            self.status_label.setText(f"Hide all: {len(token_ids)} token")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore hide all: {exc}")

    def _on_reset(self) -> None:
        try:
            self.controller.reset()
            self.status_label.setText("Sessione resettata")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore reset: {exc}")

    def _on_scene_token_flip(self, token_id: str) -> None:
        try:
            new_state = self.controller.flip_token(token_id)
            self.status_label.setText(f"Flip token: {token_id} -> {new_state}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore flip: {exc}")

    def _refresh_list(self) -> None:
        selected_ids = self._checked_token_ids_from_ui()
        entries = self.controller.token_status_entries(selected_ids)

        self.token_list.clear()
        for entry in entries:
            item = QListWidgetItem(f"{entry['name']} | {entry['status']}")
            item.setData(Qt.ItemDataRole.UserRole, str(entry["token_id"]))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            if entry["in_session"]:
                is_checked = True
            else:
                is_checked = entry["token_id"] in selected_ids

            item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            self.token_list.addItem(item)

        self._refresh_scene()

    def _refresh_scene(self) -> None:
        self.table_scene.load_from_session(self.controller.scene_entries())

    def _checked_token_ids_from_ui(self) -> set:
        selected = set()
        for index in range(self.token_list.count()):
            item = self.token_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                token_id = item.data(Qt.ItemDataRole.UserRole)
                if token_id:
                    from uuid import UUID

                    selected.add(UUID(token_id))
        return selected


def main(base_dir: str | Path = ".runtime/gui") -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(controller=MainController(base_dir=base_dir))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
