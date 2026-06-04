import os
from pathlib import Path
import re
import time

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGraphicsView,
    QGridLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStyle,
    QSpinBox,
    QSplitter,
    QSplitterHandle,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.gui_pyqt.controllers.main_controller import MainController
from src.core.models.enums import TokenShape
from src.gui_pyqt.scene.token_table_scene import TokenTableScene


class _TokenPaneSplitterHandle(QSplitterHandle):
    def mouseDoubleClickEvent(self, event) -> None:
        splitter = self.splitter()
        if isinstance(splitter, _TokenPaneSplitter):
            splitter.toggle_left_panel()
        super().mouseDoubleClickEvent(event)


class _TokenPaneSplitter(QSplitter):
    def __init__(self, on_toggle, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._on_toggle = on_toggle

    def createHandle(self) -> QSplitterHandle:
        return _TokenPaneSplitterHandle(self.orientation(), self)

    def toggle_left_panel(self) -> None:
        self._on_toggle()


class TokenEditDialog(QDialog):
    MODE_TEXT_ONLY = "text_only"
    MODE_IMAGE_ONLY = "image_only"
    MODE_IMAGE_TEXT_BLACK = "image_text_black"
    MODE_IMAGE_TEXT_WHITE = "image_text_white"
    MODE_IMAGE_TEXT_AUTO = "image_text_auto"

    def __init__(
        self,
        *,
        default_text: str,
        default_tip_text: str,
        default_tags: list[str],
        default_shape: TokenShape,
        default_mode: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Modifica Token Selezionati")
        self.setMinimumWidth(720)

        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.text_edit = QLineEdit(default_text)
        self.text_edit.setMinimumWidth(520)
        form.addRow("Testo:", self.text_edit)

        self.tip_text_edit = QTextEdit()
        self.tip_text_edit.setPlainText(default_tip_text)
        self.tip_text_edit.setMinimumHeight(120)
        self.tip_text_edit.setPlaceholderText("Testo overlay sotto il token al passaggio mouse")
        form.addRow("Tip Text:", self.tip_text_edit)

        self.tags_edit = QLineEdit("; ".join(default_tags))
        self.tags_edit.setPlaceholderText("tag1; tag2 oppure tag1, tag2")
        form.addRow("Tag:", self.tags_edit)

        self.shape_combo = QComboBox()
        for shape in TokenShape:
            self.shape_combo.addItem(shape.value, shape)
        index = self.shape_combo.findData(default_shape)
        if index >= 0:
            self.shape_combo.setCurrentIndex(index)
        form.addRow("Forma:", self.shape_combo)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Solo Testo", self.MODE_TEXT_ONLY)
        self.mode_combo.addItem("Solo Immagine", self.MODE_IMAGE_ONLY)
        self.mode_combo.addItem("Imm+Testo Nero", self.MODE_IMAGE_TEXT_BLACK)
        self.mode_combo.addItem("Imm+Testo Bianco", self.MODE_IMAGE_TEXT_WHITE)
        self.mode_combo.addItem("Imm+Testo Auto", self.MODE_IMAGE_TEXT_AUTO)
        mode_index = self.mode_combo.findData(default_mode)
        if mode_index >= 0:
            self.mode_combo.setCurrentIndex(mode_index)
        form.addRow("Modalita:", self.mode_combo)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        form.addRow(self.button_box)

    def values(self) -> tuple[str, str, str, TokenShape, str]:
        shape = self.shape_combo.currentData()
        if not isinstance(shape, TokenShape):
            shape = TokenShape.CIRCLE
        mode = self.mode_combo.currentData()
        if not isinstance(mode, str):
            mode = self.MODE_TEXT_ONLY
        return (
            self.text_edit.text(),
            self.tip_text_edit.toPlainText(),
            self.tags_edit.text(),
            shape,
            mode,
        )


class TokenTreeWidget(QTreeWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)

    def _leaf_items(self) -> list[QTreeWidgetItem]:
        leaves: list[QTreeWidgetItem] = []

        def collect(node: QTreeWidgetItem) -> None:
            if node.childCount() <= 0:
                token_id = node.data(0, Qt.ItemDataRole.UserRole)
                if token_id:
                    leaves.append(node)
                return
            for idx in range(node.childCount()):
                collect(node.child(idx))

        for idx in range(self.topLevelItemCount()):
            collect(self.topLevelItem(idx))
        return leaves

    class _LeafAdapter:
        def __init__(self, item: QTreeWidgetItem) -> None:
            self._item = item

        def checkState(self, *args):
            if len(args) <= 0:
                return self._item.checkState(0)
            return self._item.checkState(args[0])

        def setCheckState(self, *args) -> None:
            if len(args) == 1:
                self._item.setCheckState(0, args[0])
                return
            self._item.setCheckState(args[0], args[1])

        def data(self, *args):
            if len(args) == 1:
                return self._item.data(0, args[0])
            return self._item.data(args[0], args[1])

        def text(self, *args):
            if len(args) <= 0:
                return self._item.text(0)
            return self._item.text(args[0])

        def __getattr__(self, attr: str):
            return getattr(self._item, attr)

    def count(self) -> int:
        return len(self._leaf_items())

    def item(self, index: int):
        return self._LeafAdapter(self._leaf_items()[index])


class MainWindow(QMainWindow):
    def __init__(self, controller: MainController | None = None) -> None:
        super().__init__()
        self.controller = controller or MainController()
        self._is_refreshing_scene = False
        self._last_inserted_token_ids: set[str] = set()
        self._last_list_panel_size = 260
        self._flip_animation_enabled = os.environ.get("QT_QPA_PLATFORM", "").lower() != "offscreen"
        self._flip_debounce_seconds = 0.120
        self._last_flip_request_at: dict[str, float] = {}
        self._flip_duration_ms = 220
        self._move_duration_ms = 260
        self._auto_sort_delay_seconds = 0.0
        self._auto_shuffle_after_insert_count = 3
        self._is_tree_check_propagating = False
        self._auto_sort_timer = QTimer(self)
        self._auto_sort_timer.setSingleShot(True)
        self._auto_sort_timer.timeout.connect(self._on_auto_sort_timeout)

        self.setWindowTitle("Fate-Bag - GUI Tecnica Minima")
        self.resize(760, 480)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        self.controls_grid = QGridLayout()

        self.load_tokens_btn = QPushButton("Carica Token")
        self.load_tokens_btn.setObjectName("load_tokens_btn")
        self.controls_grid.addWidget(self.load_tokens_btn, 0, 0)

        self.create_selected_session_btn = QPushButton("Inserisci in Bag")
        self.create_selected_session_btn.setObjectName("create_selected_session_btn")
        self.controls_grid.addWidget(self.create_selected_session_btn, 1, 0)

        self.select_all_btn = QPushButton("")
        self.select_all_btn.setObjectName("select_all_btn")
        self.select_all_btn.setToolTip("Seleziona Tutto")
        self.select_all_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        )
        self.controls_grid.addWidget(self.select_all_btn, 0, 1)

        self.deselect_all_btn = QPushButton("")
        self.deselect_all_btn.setObjectName("deselect_all_btn")
        self.deselect_all_btn.setToolTip("Deseleziona Tutto")
        self.deselect_all_btn.setIcon(self._icon_empty_checkbox())
        self.controls_grid.addWidget(self.deselect_all_btn, 1, 1)

        self.new_token_btn = QPushButton("+")
        self.new_token_btn.setObjectName("new_token_btn")
        self.new_token_btn.setToolTip("New Token (1)")
        self.new_token_btn.setText("")
        self.new_token_btn.setIcon(self._icon_plus())
        self.controls_grid.addWidget(self.new_token_btn, 0, 2)

        self.delete_token_btn = QPushButton("X")
        self.delete_token_btn.setObjectName("delete_token_btn")
        self.delete_token_btn.setToolTip("Delete Token selezionati")
        self.delete_token_btn.setText("")
        self.delete_token_btn.setIcon(self._icon_red_x())
        self.controls_grid.addWidget(self.delete_token_btn, 1, 2)

        self.front_img_upload_btn = QPushButton("Front-Img Upload")
        self.front_img_upload_btn.setObjectName("front_img_upload_btn")
        self.controls_grid.addWidget(self.front_img_upload_btn, 0, 3)

        self.front_img_delete_btn = QPushButton("Front-Img Delete")
        self.front_img_delete_btn.setObjectName("front_img_delete_btn")
        self.controls_grid.addWidget(self.front_img_delete_btn, 1, 3)

        self.back_img_upload_btn = QPushButton("Back-Img Upload")
        self.back_img_upload_btn.setObjectName("back_img_upload_btn")
        self.controls_grid.addWidget(self.back_img_upload_btn, 0, 4)

        self.back_img_delete_btn = QPushButton("Back-Img Delete")
        self.back_img_delete_btn.setObjectName("back_img_delete_btn")
        self.controls_grid.addWidget(self.back_img_delete_btn, 1, 4)

        self.shuffle_btn = QPushButton("Shuffle")
        self.shuffle_btn.setObjectName("shuffle_btn")
        self.controls_grid.addWidget(self.shuffle_btn, 0, 5)

        self.sort_btn = QPushButton("Sort")
        self.sort_btn.setObjectName("sort_btn")
        self.controls_grid.addWidget(self.sort_btn, 1, 5)

        self.draw_n_spin = QSpinBox()
        self.draw_n_spin.setObjectName("draw_n_spin")
        self.draw_n_spin.setMinimum(1)
        self.draw_n_spin.setMaximum(99)
        self.draw_n_spin.setValue(2)
        self.controls_grid.addWidget(self.draw_n_spin, 0, 6)

        self.draw_n_btn = QPushButton("Pesca N")
        self.draw_n_btn.setObjectName("draw_n_btn")
        self.controls_grid.addWidget(self.draw_n_btn, 1, 6)

        self.draw_one_btn = QPushButton("Pesca 1")
        self.draw_one_btn.setObjectName("draw_one_btn")
        self.controls_grid.addWidget(self.draw_one_btn, 0, 7)

        self.draw_all_btn = QPushButton("Pesca Tutte")
        self.draw_all_btn.setObjectName("draw_all_btn")
        self.controls_grid.addWidget(self.draw_all_btn, 1, 7)

        self.reinsert_bag_btn = QPushButton("Rimetti in Bag")
        self.reinsert_bag_btn.setObjectName("reinsert_bag_btn")
        self.controls_grid.addWidget(self.reinsert_bag_btn, 0, 8)

        self.reset_btn = QPushButton("Svuota Bag")
        self.reset_btn.setObjectName("reset_btn")
        self.controls_grid.addWidget(self.reset_btn, 1, 8)

        layout.addLayout(self.controls_grid)

        self.status_label = QLabel("Pronto")
        self.status_label.setObjectName("status_label")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.content_splitter = _TokenPaneSplitter(self._toggle_token_list_visibility, self)
        self.content_splitter.setObjectName("content_splitter")
        self.content_splitter.setChildrenCollapsible(True)
        self.content_splitter.setHandleWidth(8)

        self.token_list = TokenTreeWidget()
        self.token_list.setObjectName("token_list")
        self.content_splitter.addWidget(self.token_list)

        self.table_scene = TokenTableScene()
        self.table_view = QGraphicsView(self.table_scene)
        self.table_view.setObjectName("table_view")
        self.table_view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.table_view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.content_splitter.addWidget(self.table_view)

        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setSizes([self._last_list_panel_size, 500])

        layout.addWidget(self.content_splitter, 1)
        self._sync_table_scene_to_viewport()

    def _connect_signals(self) -> None:
        self.load_tokens_btn.clicked.connect(self._on_load_tokens)
        self.create_selected_session_btn.clicked.connect(self._on_create_session_from_selection)
        self.new_token_btn.clicked.connect(self._on_new_token)
        self.delete_token_btn.clicked.connect(self._on_delete_selected_tokens)
        self.reinsert_bag_btn.clicked.connect(self._on_reinsert_bag)
        self.select_all_btn.clicked.connect(self._on_select_all_tokens)
        self.deselect_all_btn.clicked.connect(self._on_deselect_all_tokens)
        self.draw_one_btn.clicked.connect(self._on_draw_one)
        self.draw_all_btn.clicked.connect(self._on_draw_all)
        self.draw_n_btn.clicked.connect(self._on_draw_n)
        self.shuffle_btn.clicked.connect(self._on_shuffle)
        self.sort_btn.clicked.connect(self._on_sort)
        self.front_img_upload_btn.clicked.connect(self._on_front_img_upload)
        self.front_img_delete_btn.clicked.connect(self._on_front_img_delete)
        self.back_img_upload_btn.clicked.connect(self._on_back_img_upload)
        self.back_img_delete_btn.clicked.connect(self._on_back_img_delete)
        self.reset_btn.clicked.connect(self._on_reset)

        self.table_scene.token_selected.connect(self._on_scene_token_selected)
        self.table_scene.token_selection_changed.connect(self._on_scene_selection_changed)
        self.table_scene.token_flip_requested.connect(self._on_scene_token_flip)
        self.table_scene.token_dragged.connect(self._on_scene_token_dragged)

        self.token_list.itemDoubleClicked.connect(self._on_token_list_item_double_clicked)
        self.token_list.itemChanged.connect(self._on_token_list_item_changed)

    def _on_load_tokens(self, token_file: str | bool | None = None) -> None:
        try:
            chosen_file: str | None
            if isinstance(token_file, bool):
                chosen_file = None
            else:
                chosen_file = token_file

            if chosen_file is None and self.sender() is self.load_tokens_btn:
                chosen_file = self._pick_token_json_file()
                if not chosen_file:
                    self.status_label.setText("Caricamento token annullato")
                    return

            tokens = self.controller.load_tokens(chosen_file)
            self._apply_table_visual_settings_from_tokens_config()
            self._resize_window_for_table_background()
            self._last_inserted_token_ids.clear()
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
            self._insert_selected_into_bag(selected_ids, status_prefix="Inseriti in Bag")
        except Exception as exc:
            self.status_label.setText(f"Errore create session da selezione: {exc}")

    def _on_new_token(self) -> None:
        try:
            token = self.controller.create_new_token()
            self.status_label.setText(f"Nuovo token creato: {token.name}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore new token: {exc}")

    def _on_delete_selected_tokens(self) -> None:
        try:
            selected_ids = list(self._checked_token_ids_from_ui())
            deleted_count = self.controller.delete_tokens(selected_ids)
            self._last_inserted_token_ids = {
                token_id
                for token_id in self._last_inserted_token_ids
                if token_id not in {str(value) for value in selected_ids}
            }
            self.status_label.setText(f"Token eliminati: {deleted_count}")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore delete token: {exc}")

    def _on_reinsert_bag(self) -> None:
        try:
            if not self._last_inserted_token_ids:
                raise ValueError("Nessun inserimento precedente da rimettere")

            self._set_checkboxes_from_token_ids(self._last_inserted_token_ids)
            self._sync_scene_selection_from_checkboxes()
            selected_ids = list(self._checked_token_ids_from_ui())
            self._insert_selected_into_bag(selected_ids, status_prefix="Rimessi in Bag")
        except Exception as exc:
            self.status_label.setText(f"Errore rimetti in bag: {exc}")

    def _on_select_all_tokens(self) -> None:
        for index in range(self.token_list.count()):
            self.token_list.item(index).setCheckState(0, Qt.CheckState.Checked)
        self.status_label.setText("Tutti i token selezionati")

    def _on_deselect_all_tokens(self) -> None:
        for index in range(self.token_list.count()):
            self.token_list.item(index).setCheckState(0, Qt.CheckState.Unchecked)
        self.status_label.setText("Tutti i token deselezionati")

    def _on_draw_one(self) -> None:
        try:
            drawn = self.controller.draw_one()
            status = self._draw_status_text("Pesca 1", drawn)
            self._refresh_list()
            self._animate_tokens_flip_visual(drawn, status_text=status)
            self._schedule_auto_sort_after_draw(trigger_label="Pesca 1")
        except Exception as exc:
            self.status_label.setText(f"Errore draw 1: {exc}")

    def _on_draw_all(self) -> None:
        try:
            drawn = self.controller.draw_all()
            status = self._draw_status_text("Pesca Tutte", drawn)
            self._refresh_list()
            self._animate_tokens_flip_visual(drawn, status_text=status)
        except Exception as exc:
            self.status_label.setText(f"Errore pesca tutte: {exc}")

    def _on_draw_n(self) -> None:
        try:
            drawn = self.controller.draw_many(self.draw_n_spin.value())
            status = self._draw_status_text("Pesca N", drawn)
            self._refresh_list()
            self._animate_tokens_flip_visual(drawn, status_text=status)
            self._schedule_auto_sort_after_draw(trigger_label="Pesca N")
        except Exception as exc:
            self.status_label.setText(f"Errore draw N: {exc}")

    def _on_shuffle(self) -> None:
        try:
            self.controller.shuffle()
            self._refresh_token_list_only()
            self.table_scene.animate_tokens_to_core_positions(
                self.controller.scene_entries(),
                duration_ms=self._move_duration_ms,
            )
            self.status_label.setText("Shuffle eseguito")
        except Exception as exc:
            self.status_label.setText(f"Errore shuffle: {exc}")

    def _on_sort(self) -> None:
        try:
            if self._auto_sort_timer.isActive():
                self._auto_sort_timer.stop()
            self.controller.sort_face_up_first()
            self._refresh_token_list_only()
            self.table_scene.animate_tokens_to_core_positions(
                self.controller.scene_entries(),
                duration_ms=self._move_duration_ms,
            )
            self.status_label.setText("Sort eseguito (FACE_UP -> FACE_DOWN)")
        except Exception as exc:
            self.status_label.setText(f"Errore sort: {exc}")

    def _on_auto_sort_timeout(self) -> None:
        self._on_sort()

    def _schedule_auto_sort_after_draw(self, *, trigger_label: str) -> None:
        delay_seconds = max(0.0, float(self._auto_sort_delay_seconds))
        if delay_seconds <= 0.0:
            if self._auto_sort_timer.isActive():
                self._auto_sort_timer.stop()
            return

        delay_ms = max(1, int(round(delay_seconds * 1000.0)))
        self._auto_sort_timer.start(delay_ms)
        self.status_label.setText(
            f"{trigger_label}: sort automatico tra {delay_seconds:g}s"
        )

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
        item: QTreeWidgetItem,
        column: int = 0,
        text: str | None = None,
        tip_text: str | None = None,
        tags_text: str | None = None,
        shape: TokenShape | None = None,
        display_mode: str | None = None,
    ) -> None:
        del column
        try:
            clicked_token_id = item.data(0, Qt.ItemDataRole.UserRole)
            if not clicked_token_id:
                return

            from uuid import UUID

            clicked_uuid = UUID(clicked_token_id)
            if item.checkState(0) != Qt.CheckState.Checked:
                item.setCheckState(0, Qt.CheckState.Checked)
            selected_ids = list(self._checked_token_ids_from_ui())
            target_ids = selected_ids if selected_ids else [clicked_uuid]

            clicked_token = self.controller.token_for_id(clicked_uuid)

            name_value = text
            tip_text_value = tip_text
            tags_value = tags_text
            shape_value = shape
            mode_value = display_mode

            if (
                name_value is None
                and tip_text_value is None
                and tags_value is None
                and shape_value is None
                and mode_value is None
            ):
                default_mode = self._display_mode_for_token(clicked_token)
                dialog = TokenEditDialog(
                    default_text=self.controller.front_text_for_token(clicked_uuid),
                    default_tip_text=self.controller.tip_text_for_token(clicked_uuid),
                    default_tags=clicked_token.tags,
                    default_shape=clicked_token.shape,
                    default_mode=default_mode,
                    parent=self,
                )
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    self.status_label.setText("Modifica token annullata")
                    return

                dialog_name, dialog_tip_text, dialog_tags, dialog_shape, dialog_mode = dialog.values()
                if name_value is None:
                    name_value = dialog_name
                if tip_text_value is None:
                    tip_text_value = dialog_tip_text
                if tags_value is None:
                    tags_value = dialog_tags
                if shape_value is None:
                    shape_value = dialog_shape
                if mode_value is None:
                    mode_value = dialog_mode

            if name_value is None:
                name_value = clicked_token.name
            if tip_text_value is None:
                tip_text_value = self.controller.tip_text_for_token(clicked_uuid)
            if tags_value is None:
                tags_value = "; ".join(clicked_token.tags)
            if shape_value is None:
                shape_value = clicked_token.shape
            if mode_value is None:
                mode_value = self._display_mode_for_token(clicked_token)

            parsed_tags = self._parse_tags_input(tags_value or "")
            chosen_shape = shape_value if isinstance(shape_value, TokenShape) else clicked_token.shape

            updated_count = self.controller.apply_token_metadata_to_tokens(
                target_ids,
                text=name_value or clicked_token.name,
                tip_text=tip_text_value,
                tags=parsed_tags,
                shape=chosen_shape,
                display_mode=mode_value,
            )
            self.status_label.setText(f"Token aggiornati da lista su {updated_count} token")
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
            self.controller.clear_bag()
            self.token_list.blockSignals(True)
            for index in range(self.token_list.count()):
                self.token_list.item(index).setCheckState(0, Qt.CheckState.Unchecked)
            self.token_list.blockSignals(False)
            self.status_label.setText("Bag svuotato")
            self._refresh_list()
        except Exception as exc:
            self.status_label.setText(f"Errore reset: {exc}")

    def _on_scene_token_flip(self, token_id: str) -> None:
        try:
            now = time.monotonic()
            last_time = self._last_flip_request_at.get(token_id)
            if last_time is not None and (now - last_time) < self._flip_debounce_seconds:
                self.status_label.setText("Flip ignorato (debounce)")
                return
            self._last_flip_request_at[token_id] = now

            self._set_checkbox_checked(token_id)
            if self._flip_animation_enabled and self.table_scene.is_token_flip_animating(token_id):
                self.status_label.setText("Flip in corso")
                return

            new_state = self.controller.flip_token(token_id)
            status = f"Flip token: {token_id} -> {new_state}"
            self._refresh_list()
            self._animate_tokens_flip_visual([token_id], status_text=status)
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

        self._populate_token_tree(entries, selected_ids)

        self._refresh_scene_preserve_checkbox_selection()

    def _refresh_token_list_only(self) -> None:
        selected_ids = self._checked_token_ids_from_ui()
        entries = self.controller.token_status_entries(selected_ids)

        self._populate_token_tree(entries, selected_ids)

        self._sync_scene_selection_from_checkboxes()

    def _populate_token_tree(self, entries: list[dict], selected_ids: set) -> None:
        self.token_list.clear()
        self.token_list.blockSignals(True)

        category_nodes: dict[tuple[str, ...], QTreeWidgetItem] = {}

        for entry in entries:
            category_path = self._primary_category_path(entry.get("categories", []))
            parent_node = self._get_or_create_category_node(category_nodes, category_path)

            display_name = self._display_name_for_list(str(entry["name"]))
            tags = entry.get("tags", [])
            tags_text = ", ".join(tags) if tags else "-"
            row_text = (
                f"{display_name} | {entry['status']} | "
                f"{entry.get('shape', '-')} | #: {tags_text}"
            )

            item = QTreeWidgetItem([row_text])
            item.setData(0, Qt.ItemDataRole.UserRole, str(entry["token_id"]))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            is_checked = entry["token_id"] in selected_ids
            item.setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
            parent_node.addChild(item)

        self._update_all_parent_check_states()
        self.token_list.expandAll()
        self.token_list.blockSignals(False)

    def _get_or_create_category_node(
        self,
        nodes: dict[tuple[str, ...], QTreeWidgetItem],
        path: tuple[str, ...],
    ) -> QTreeWidgetItem:
        if not path:
            path = ("Senza Categoria",)

        current_parent: QTreeWidgetItem | None = None
        for depth in range(1, len(path) + 1):
            current_path = path[:depth]
            existing = nodes.get(current_path)
            if existing is None:
                label = current_path[-1]
                existing = QTreeWidgetItem([label])
                existing.setFlags(existing.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                existing.setCheckState(0, Qt.CheckState.Unchecked)
                nodes[current_path] = existing
                if current_parent is None:
                    self.token_list.addTopLevelItem(existing)
                else:
                    current_parent.addChild(existing)
            current_parent = existing

        if current_parent is None:
            fallback = QTreeWidgetItem(["Senza Categoria"])
            fallback.setFlags(fallback.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            fallback.setCheckState(0, Qt.CheckState.Unchecked)
            self.token_list.addTopLevelItem(fallback)
            return fallback
        return current_parent

    @staticmethod
    def _primary_category_path(categories: object) -> tuple[str, ...]:
        if not isinstance(categories, list):
            return tuple()

        for raw in categories:
            if not isinstance(raw, str):
                continue
            text = raw.strip()
            if not text:
                continue
            chunks = [part.strip() for part in text.split(">") if part.strip()]
            if chunks:
                return tuple(chunks)
        return tuple()

    def _refresh_scene(self) -> None:
        self._sync_table_scene_to_viewport()
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
            if item.checkState(0) == Qt.CheckState.Checked:
                token_id = item.data(0, Qt.ItemDataRole.UserRole)
                if token_id:
                    from uuid import UUID

                    selected.add(UUID(token_id))
        return selected

    def _pick_image_file(self, title: str) -> str | None:
        initial_dir = self._default_assets_root_directory()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            initial_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*.*)",
        )
        if not file_path:
            return None
        return file_path

    def _pick_token_json_file(self) -> str | None:
        initial_dir = self._default_tokens_directory()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleziona file JSON token",
            initial_dir,
            "JSON (*.json);;All files (*.*)",
        )
        if not file_path:
            return None
        return file_path

    def _default_tokens_directory(self) -> str:
        bootstrap_file = self.controller.bootstrap_tokens_file
        candidate = bootstrap_file if bootstrap_file.is_absolute() else (Path.cwd() / bootstrap_file)
        if candidate.exists():
            return str(candidate.parent)

        if bootstrap_file.parent.exists():
            return str(bootstrap_file.parent)

        fallback = Path.cwd() / "config"
        return str(fallback if fallback.exists() else Path.cwd())

    def _default_assets_root_directory(self) -> str:
        settings = self.controller.token_file_settings
        raw_assets_root = settings.get("assets_root_path")
        if isinstance(raw_assets_root, str) and raw_assets_root.strip():
            candidate = Path(raw_assets_root)
            if candidate.exists():
                return str(candidate)

        return self._default_tokens_directory()

    @staticmethod
    def _parse_tags_input(raw_tags: str) -> list[str]:
        normalized = raw_tags.replace(";", ",")
        return [chunk.strip() for chunk in normalized.split(",") if chunk.strip()]

    def _set_checkbox_checked(self, token_id: str) -> bool:
        for index in range(self.token_list.count()):
            item = self.token_list.item(index)
            row_token_id = item.data(0, Qt.ItemDataRole.UserRole)
            if row_token_id == token_id:
                if item.checkState(0) != Qt.CheckState.Checked:
                    item.setCheckState(0, Qt.CheckState.Checked)
                    self._sync_scene_selection_from_checkboxes()
                    return True
                return False
        return False

    def _set_checkbox_exclusive(self, token_id: str) -> bool:
        changed = False
        for index in range(self.token_list.count()):
            item = self.token_list.item(index)
            row_token_id = item.data(0, Qt.ItemDataRole.UserRole)
            should_check = row_token_id == token_id
            desired = Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked
            if item.checkState(0) != desired:
                item.setCheckState(0, desired)
                changed = True
        self._sync_scene_selection_from_checkboxes()
        return changed

    def _on_token_list_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        del column
        if self._is_tree_check_propagating:
            return

        self._is_tree_check_propagating = True
        try:
            state = item.checkState(0)
            self._set_descendants_check_state(item, state)
            self._update_parent_check_states(item.parent())
        finally:
            self._is_tree_check_propagating = False

        self._sync_scene_selection_from_checkboxes()

    def _set_descendants_check_state(self, node: QTreeWidgetItem, state: Qt.CheckState) -> None:
        for idx in range(node.childCount()):
            child = node.child(idx)
            child.setCheckState(0, state)
            self._set_descendants_check_state(child, state)

    def _update_parent_check_states(self, parent: QTreeWidgetItem | None) -> None:
        current = parent
        while current is not None:
            checked = 0
            partial = 0
            total = current.childCount()
            for idx in range(total):
                child_state = current.child(idx).checkState(0)
                if child_state == Qt.CheckState.Checked:
                    checked += 1
                elif child_state == Qt.CheckState.PartiallyChecked:
                    partial += 1

            if checked == total and total > 0:
                current.setCheckState(0, Qt.CheckState.Checked)
            elif checked == 0 and partial == 0:
                current.setCheckState(0, Qt.CheckState.Unchecked)
            else:
                current.setCheckState(0, Qt.CheckState.PartiallyChecked)
            current = current.parent()

    def _update_all_parent_check_states(self) -> None:
        for idx in range(self.token_list.topLevelItemCount()):
            top_node = self.token_list.topLevelItem(idx)
            self._update_node_check_state_from_children(top_node)

    def _update_node_check_state_from_children(self, node: QTreeWidgetItem) -> Qt.CheckState:
        if node.childCount() <= 0:
            return node.checkState(0)

        child_states = [self._update_node_check_state_from_children(node.child(i)) for i in range(node.childCount())]
        if all(state == Qt.CheckState.Checked for state in child_states):
            node.setCheckState(0, Qt.CheckState.Checked)
        elif all(state == Qt.CheckState.Unchecked for state in child_states):
            node.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            node.setCheckState(0, Qt.CheckState.PartiallyChecked)
        return node.checkState(0)

    def _set_checkboxes_from_token_ids(self, selected_token_ids: set[str]) -> None:
        self.token_list.blockSignals(True)
        for index in range(self.token_list.count()):
            item = self.token_list.item(index)
            row_token_id = item.data(0, Qt.ItemDataRole.UserRole)
            should_check = row_token_id in selected_token_ids
            item.setCheckState(0, Qt.CheckState.Checked if should_check else Qt.CheckState.Unchecked)
        self._update_all_parent_check_states()
        self.token_list.blockSignals(False)

    def _sync_scene_selection_from_checkboxes(self) -> None:
        selected = {
            str(token_id)
            for token_id in self._checked_token_ids_from_ui()
        }
        self.table_scene.set_selected_token_ids(selected)

    def _toggle_token_list_visibility(self) -> None:
        sizes = self.content_splitter.sizes()
        if len(sizes) < 2:
            return

        list_size, table_size = sizes
        total = max(1, list_size + table_size)

        if list_size > 0:
            self._last_list_panel_size = max(120, list_size)
            self.content_splitter.setSizes([0, total])
            self.status_label.setText("Lista checkbox nascosta")
        else:
            restored = min(max(120, self._last_list_panel_size), total - 1)
            self.content_splitter.setSizes([restored, total - restored])
            self.status_label.setText("Lista checkbox visibile")

        self._sync_table_scene_to_viewport()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_table_scene_to_viewport()

    def _sync_table_scene_to_viewport(self) -> None:
        viewport = self.table_view.viewport().size()
        self.table_scene.update_viewport_rect(viewport.width(), viewport.height())

    def _apply_table_visual_settings_from_tokens_config(self) -> None:
        settings = self.controller.token_file_settings
        self.table_scene.apply_visual_settings(
            token_radius_px=settings.get("token_radius_px"),
            table_grid_margin_px=settings.get("table_grid_margin_px"),
            hover_preview_enabled=settings.get("hover_preview_enabled"),
            front_text_font_px=settings.get("front_text_font_px"),
            tip_text_font_px=settings.get("tip_text_font_px"),
            table_background_file=settings.get("table_background_file"),
        )
        self._flip_duration_ms = self._flip_duration_from_speed(settings.get("flip_speed"))
        self._move_duration_ms = self._move_duration_from_speed(settings.get("move_speed"))
        self._auto_sort_delay_seconds = self._auto_sort_delay_seconds_from_value(
            settings.get("auto_sort_delay_seconds")
        )
        self._auto_shuffle_after_insert_count = self._auto_shuffle_count_from_value(
            settings.get("auto_shuffle_after_insert_count")
        )
        if self._auto_sort_delay_seconds <= 0.0 and self._auto_sort_timer.isActive():
            self._auto_sort_timer.stop()
        self._sync_table_scene_to_viewport()

    def _resize_window_for_table_background(self) -> None:
        bg_width, bg_height = self.table_scene.table_background_size()
        if bg_width <= 0 or bg_height <= 0:
            return

        min_window_width = max(self.minimumWidth(), 520)
        min_window_height = max(self.minimumHeight(), 360)
        for _ in range(3):
            QApplication.processEvents()
            viewport = self.table_view.viewport().size()
            hidden_table_panel_width = self.content_splitter.width()
            if viewport.width() <= 0 or viewport.height() <= 0:
                return

            width_delta = bg_width - hidden_table_panel_width
            height_delta = bg_height - viewport.height()
            if abs(width_delta) <= 1 and abs(height_delta) <= 1:
                break

            target_width = max(min_window_width, self.width() + width_delta)
            target_height = max(min_window_height, self.height() + height_delta)
            self.resize(int(target_width), int(target_height))

        self._center_window_on_screen()

    def _center_window_on_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return

        available = screen.availableGeometry()
        frame = self.frameGeometry()
        target_x = available.left() + max(0, (available.width() - frame.width()) // 2)
        target_y = available.top() + max(0, (available.height() - frame.height()) // 2)
        self.move(target_x, target_y)

    def _insert_selected_into_bag(self, selected_ids: list, *, status_prefix: str) -> None:
        session = self.controller.create_session_from_selection(selected_ids)
        self._last_inserted_token_ids = {
            str(table_token.token_id)
            for table_token in session.table_tokens
        }
        self._refresh_list()

        shuffle_count = max(0, int(self._auto_shuffle_after_insert_count))
        if shuffle_count > 0:
            for _ in range(shuffle_count):
                self.controller.shuffle()

            self._refresh_token_list_only()
            self.table_scene.animate_tokens_to_core_positions(
                self.controller.scene_entries(),
                duration_ms=self._move_duration_ms,
            )

        status_text = f"{status_prefix}: {session.session_id}"
        if shuffle_count > 0:
            status_text = f"{status_text} | Auto Shuffle x{shuffle_count}"

        self._animate_tokens_flip_visual(
            list(self._last_inserted_token_ids),
            status_text=status_text,
        )

    def _animate_tokens_flip_visual(self, token_ids: list[str], *, status_text: str) -> None:
        self.status_label.setText(status_text)
        if not self._flip_animation_enabled:
            return

        pending = 0
        seen: set[str] = set()
        for token_id in token_ids:
            token_key = str(token_id)
            if token_key in seen:
                continue
            seen.add(token_key)
            if self.table_scene.is_token_flip_animating(token_key):
                continue
            started = self.table_scene.animate_token_flip(token_key, duration_ms=self._flip_duration_ms)
            if started:
                pending += 1

        if pending <= 0:
            return

    @staticmethod
    def _draw_status_text(prefix: str, drawn_ids: list[str]) -> str:
        count = len(drawn_ids)
        return f"{prefix}: {count} token"

    @staticmethod
    def _flip_duration_from_speed(raw_speed: object) -> int:
        speed_value = 60
        if isinstance(raw_speed, (int, float)):
            speed_value = int(round(float(raw_speed)))
        speed_value = max(1, min(100, speed_value))

        # 1 => slowest, 100 => fastest.
        min_duration = 1
        max_duration = 100
        span = max_duration - min_duration
        ratio = (speed_value - 1) / 99
        return int(round(max_duration - (span * ratio)))

    @staticmethod
    def _move_duration_from_speed(raw_speed: object) -> int:
        speed_value = 60
        if isinstance(raw_speed, (int, float)):
            speed_value = int(round(float(raw_speed)))
        speed_value = max(1, min(100, speed_value))

        # 1 => slowest movement, 100 => fastest movement.
        min_duration = 90
        max_duration = 900
        span = max_duration - min_duration
        ratio = (speed_value - 1) / 99
        return int(round(max_duration - (span * ratio)))

    @staticmethod
    def _auto_sort_delay_seconds_from_value(raw_value: object) -> float:
        if isinstance(raw_value, (int, float)):
            return max(0.0, float(raw_value))
        return 0.0

    @staticmethod
    def _auto_shuffle_count_from_value(raw_value: object) -> int:
        if isinstance(raw_value, (int, float)):
            return max(0, int(round(float(raw_value))))
        return 3

    @staticmethod
    def _display_mode_for_token(token) -> str:
        from src.core.models.enums import TokenFrontType

        if token.front_type == TokenFrontType.TEXT:
            return TokenEditDialog.MODE_TEXT_ONLY
        if token.front_type == TokenFrontType.IMAGE:
            return TokenEditDialog.MODE_IMAGE_ONLY

        color_mode = str(token.metadata.get("front_text_color_mode", "auto")).strip().lower()
        if color_mode == "black":
            return TokenEditDialog.MODE_IMAGE_TEXT_BLACK
        if color_mode == "white":
            return TokenEditDialog.MODE_IMAGE_TEXT_WHITE
        return TokenEditDialog.MODE_IMAGE_TEXT_AUTO

    @staticmethod
    def _display_name_for_list(raw_name: str) -> str:
        match = re.search(r"<\s*([^<>]+?)\s*>", raw_name)
        if match:
            return match.group(1).strip()
        return raw_name.replace("<", "").replace(">", "").strip()

    @staticmethod
    def _icon_plus(size: int = 16) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor("#2e7d32"), 2)
        painter.setPen(pen)
        mid = size // 2
        painter.drawLine(mid, 3, mid, size - 3)
        painter.drawLine(3, mid, size - 3, mid)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _icon_red_x(size: int = 16) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor("#c62828"), 2)
        painter.setPen(pen)
        painter.drawLine(3, 3, size - 3, size - 3)
        painter.drawLine(size - 3, 3, 3, size - 3)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _icon_empty_checkbox(size: int = 16) -> QIcon:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor("#7a7a7a"), 2)
        painter.setPen(pen)
        painter.drawRect(3, 3, size - 6, size - 6)
        painter.end()
        return QIcon(pixmap)


def main(base_dir: str | Path = ".runtime/gui") -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow(controller=MainController(base_dir=base_dir))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
