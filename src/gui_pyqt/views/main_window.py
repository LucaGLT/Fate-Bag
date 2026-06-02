from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.gui_pyqt.controllers.main_controller import MainController


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

        self.token_list = QListWidget()
        self.token_list.setObjectName("token_list")
        layout.addWidget(self.token_list)

    def _connect_signals(self) -> None:
        self.load_tokens_btn.clicked.connect(self._on_load_tokens)
        self.create_session_btn.clicked.connect(self._on_create_session)
        self.draw_one_btn.clicked.connect(self._on_draw_one)
        self.draw_n_btn.clicked.connect(self._on_draw_n)
        self.reveal_all_btn.clicked.connect(self._on_reveal_all)
        self.hide_all_btn.clicked.connect(self._on_hide_all)
        self.reset_btn.clicked.connect(self._on_reset)

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

    def _refresh_list(self) -> None:
        self.token_list.clear()
        for row in self.controller.table_rows():
            self.token_list.addItem(row)


def main(base_dir: str | Path = ".runtime/gui") -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(controller=MainController(base_dir=base_dir))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
