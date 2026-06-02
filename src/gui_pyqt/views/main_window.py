from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
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
        self._is_refreshing_scene = False

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

        self.create_selected_session_btn = QPushButton("Inserisci in Bag")
        self.create_selected_session_btn.setObjectName("create_selected_session_btn")
        button_row.addWidget(self.create_selected_session_btn)

        self.select_all_btn = QPushButton("Seleziona Tutto")
        self.select_all_btn.setObjectName("select_all_btn")
        button_row.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Deseleziona Tutto")
        self.deselect_all_btn.setObjectName("deselect_all_btn")
        button_row.addWidget(self.deselect_all_btn)

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

        self.front_img_upload_btn = QPushButton("Front-Img Upload")
        self.front_img_upload_btn.setObjectName("front_img_upload_btn")
        button_row.addWidget(self.front_img_upload_btn)

        self.front_img_delete_btn = QPushButton("Front-Img Delete")
        self.front_img_delete_btn.setObjectName("front_img_delete_btn")
        button_row.addWidget(self.front_img_delete_btn)

        self.front_text_edit_btn = QPushButton("Front-Text Edit")
        self.front_text_edit_btn.setObjectName("front_text_edit_btn")
        button_row.addWidget(self.front_text_edit_btn)

        self.back_img_upload_btn = QPushButton("Back-Img Upload")
        self.back_img_upload_btn.setObjectName("back_img_upload_btn")
        button_row.addWidget(self.back_img_upload_btn)

        self.back_img_delete_btn = QPushButton("Back-Img Delete")
        self.back_img_delete_btn.setObjectName("back_img_delete_btn")
        button_row.addWidget(self.back_img_delete_btn)

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
        self.create_selected_session_btn.clicked.connect(self._on_create_session_from_selection)
        self.select_all_btn.clicked.connect(self._on_select_all_tokens)
        self.deselect_all_btn.clicked.connect(self._on_deselect_all_tokens)
        self.draw_one_btn.clicked.connect(self._on_draw_one)
        self.draw_n_btn.clicked.connect(self._on_draw_n)
        self.shuffle_btn.clicked.connect(self._on_shuffle)
        self.sort_btn.clicked.connect(self._on_sort)
        self.front_img_upload_btn.clicked.connect(self._on_front_img_upload)
        self.front_img_delete_btn.clicked.connect(self._on_front_img_delete)
        self.front_text_edit_btn.clicked.connect(self._on_front_text_edit)
        self.back_img_upload_btn.clicked.connect(self._on_back_img_upload)
        self.back_img_delete_btn.clicked.connect(self._on_back_img_delete)
        self.reveal_all_btn.clicked.connect(self._on_reveal_all)
        self.hide_all_btn.clicked.connect(self._on_hide_all)
        self.reset_btn.clicked.connect(self._on_reset)
        self.table_scene.token_selected.connect(self._on_scene_token_selected)
        self.table_scene.token_selection_changed.connect(self._on_scene_selection_changed)
        self.table_scene.token_flip_requested.connect(self._on_scene_token_flip)
        self.table_scene.token_dragged.connect(self._on_scene_token_dragged)
        self.token_list.itemDoubleClicked.connect(self._on_token_list_item_double_clicked)
        self.token_list.itemChanged.connect(self._on_token_list_item_changed)

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
            self.status_label.setText(f"Inseriti in Bag: {session.session_id}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore create session da selezione: {exc}")

    def _on_select_all_tokens(self) -> None:
        for index in range(self.token_list.count()):
            self.token_list.item(index).setCheckState(Qt.CheckState.Checked)
        self.status_label.setText("Tutti i token selezionati")

    def _on_deselect_all_tokens(self) -> None:
        for index in range(self.token_list.count()):
            self.token_list.item(index).setCheckState(Qt.CheckState.Unchecked)
        self.status_label.setText("Tutti i token deselezionati")

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

    def _on_front_img_upload(self, image_path: str | None = None) -> None:
        try:
            selected_ids = list(self._checked_token_ids_from_ui())
            path = image_path or self._pick_image_file("Seleziona immagine front")
            if not path:
                self.status_label.setText("Upload front annullato")
                return

            updated_count = self.controller.apply_front_image_to_tokens(selected_ids, path)
            self.status_label.setText(f"Front image applicata a {updated_count} token")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore front upload: {exc}")

    def _on_back_img_upload(self, image_path: str | None = None) -> None:
        try:
            selected_ids = list(self._checked_token_ids_from_ui())
            path = image_path or self._pick_image_file("Seleziona immagine back")
            if not path:
                self.status_label.setText("Upload back annullato")
                return

            updated_count = self.controller.apply_back_image_to_tokens(selected_ids, path)
            self.status_label.setText(f"Back image applicata a {updated_count} token")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore back upload: {exc}")

    def _on_front_img_delete(self) -> None:
        try:
            selected_ids = list(self._checked_token_ids_from_ui())
            updated_count = self.controller.delete_front_image_from_tokens(selected_ids)
            self.status_label.setText(f"Front image rimossa da {updated_count} token")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore front delete: {exc}")

    def _on_back_img_delete(self) -> None:
        try:
            selected_ids = list(self._checked_token_ids_from_ui())
            updated_count = self.controller.delete_back_image_from_tokens(selected_ids)
            self.status_label.setText(f"Back image rimossa da {updated_count} token")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore back delete: {exc}")

    def _on_front_text_edit(self, text: str | None = None) -> None:
        try:
            selected_ids = list(self._checked_token_ids_from_ui())
            value = text if isinstance(text, str) else None
            if value is None:
                value, ok = QInputDialog.getText(self, "Front Text", "Nuovo testo front:")
                if not ok:
                    self.status_label.setText("Edit front text annullato")
                    return

            updated_count = self.controller.apply_front_text_to_tokens(selected_ids, value)
            self.status_label.setText(f"Front text aggiornato su {updated_count} token")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore front text: {exc}")

    def _on_token_list_item_double_clicked(
        self,
        item: QListWidgetItem,
        text: str | None = None,
    ) -> None:
        try:
            clicked_token_id = item.data(Qt.ItemDataRole.UserRole)
            if not clicked_token_id:
                raise ValueError("Token non valido")

            from uuid import UUID

            clicked_uuid = UUID(clicked_token_id)
            if item.checkState() != Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Checked)
            selected_ids = list(self._checked_token_ids_from_ui())
            target_ids = selected_ids if selected_ids else [clicked_uuid]

            value = text
            if value is None:
                default_text = self.controller.front_text_for_token(clicked_uuid)
                value, ok = QInputDialog.getText(
                    self,
                    "Front Text (Lista)",
                    "Nuovo testo front per i token selezionati:",
                    text=default_text,
                )
                if not ok:
                    self.status_label.setText("Edit front text da lista annullato")
                    return

            updated_count = self.controller.apply_front_text_to_tokens(target_ids, value)
            self.status_label.setText(
                f"Front text aggiornato da lista su {updated_count} token"
            )
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore edit lista: {exc}")

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
            self._set_checkbox_checked(token_id)
            new_state = self.controller.flip_token(token_id)
            self.status_label.setText(f"Flip token: {token_id} -> {new_state}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore flip: {exc}")

    def _on_scene_token_selected(self, token_id: str) -> None:
        changed = self._set_checkbox_exclusive(token_id)
        if changed:
            self.status_label.setText(f"Token selezionato: {token_id}")

    def _on_scene_selection_changed(self, selected_token_ids: set[str]) -> None:
        if self._is_refreshing_scene:
            return
        self._set_checkboxes_from_token_ids(selected_token_ids)

    def _on_scene_token_dragged(self, token_id: str, x: float, y: float) -> None:
        try:
            self._set_checkbox_checked(token_id)
            self.controller.move_token(token_id, x, y)
            self.status_label.setText(f"Token spostato: {token_id} -> ({x:.1f}, {y:.1f})")
            self._refresh_scene_preserve_checkbox_selection()
        except Exception as exc:
            self.status_label.setText(f"Errore move token: {exc}")

    def _refresh_list(self) -> None:
        selected_ids = self._checked_token_ids_from_ui()
        entries = self.controller.token_status_entries(selected_ids)

        self.token_list.clear()
        self.token_list.blockSignals(True)
        for entry in entries:
            item = QListWidgetItem(f"{entry['name']} | {entry['status']}")
            item.setData(Qt.ItemDataRole.UserRole, str(entry["token_id"]))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            is_checked = entry["token_id"] in selected_ids

            item.setCheckState(Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            self.token_list.addItem(item)
        self.token_list.blockSignals(False)

        self._refresh_scene_preserve_checkbox_selection()

    def _refresh_scene(self) -> None:
        self.table_scene.load_from_session(self.controller.scene_entries())

    def _refresh_scene_preserve_checkbox_selection(self) -> None:
        self._is_refreshing_scene = True
        self._refresh_scene()
        self._is_refreshing_scene = False
        self._sync_scene_selection_from_checkboxes()

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

    def _pick_image_file(self, title: str) -> str | None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*.*)",
        )
        if not file_path:
            return None
        return file_path

    def _set_checkbox_checked(self, token_id: str) -> bool:
        for index in range(self.token_list.count()):
            item = self.token_list.item(index)
            row_token_id = item.data(Qt.ItemDataRole.UserRole)
            if row_token_id == token_id:
                if item.checkState() != Qt.CheckState.Checked:
                    item.setCheckState(Qt.CheckState.Checked)
                    self._sync_scene_selection_from_checkboxes()
                    return True
                return False
        return False

    def _set_checkbox_exclusive(self, token_id: str) -> bool:
        changed = False
        for index in range(self.token_list.count()):
            item = self.token_list.item(index)
            row_token_id = item.data(Qt.ItemDataRole.UserRole)
            should_check = row_token_id == token_id
            desired = Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked
            if item.checkState() != desired:
                item.setCheckState(desired)
                changed = True
        self._sync_scene_selection_from_checkboxes()
        return changed

    def _on_token_list_item_changed(self, item: QListWidgetItem) -> None:
        del item
        self._sync_scene_selection_from_checkboxes()

    def _set_checkboxes_from_token_ids(self, selected_token_ids: set[str]) -> None:
        self.token_list.blockSignals(True)
        for index in range(self.token_list.count()):
            item = self.token_list.item(index)
            row_token_id = item.data(Qt.ItemDataRole.UserRole)
            should_check = row_token_id in selected_token_ids
            item.setCheckState(Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked)
        self.token_list.blockSignals(False)

    def _sync_scene_selection_from_checkboxes(self) -> None:
        selected = {
            str(token_id)
            for token_id in self._checked_token_ids_from_ui()
        }
        self.table_scene.set_selected_token_ids(selected)


def main(base_dir: str | Path = ".runtime/gui") -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(controller=MainController(base_dir=base_dir))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
