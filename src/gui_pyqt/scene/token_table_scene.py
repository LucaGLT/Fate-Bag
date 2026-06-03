from PyQt6.QtCore import QPointF, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPixmap
from PyQt6.QtWidgets import QGraphicsScene

from src.core.models.table_token import TableToken
from src.core.models.token import Token
from src.gui_pyqt.scene.token_graphics_item import TokenGraphicsItem


class TokenTableScene(QGraphicsScene):
    token_selected = pyqtSignal(str)
    token_selection_changed = pyqtSignal(object)
    token_flip_requested = pyqtSignal(str)
    token_dragged = pyqtSignal(str, float, float)

    def __init__(self, scene_width: float = 1200.0, scene_height: float = 760.0) -> None:
        super().__init__(0, 0, scene_width, scene_height)
        self._token_items: dict[str, TokenGraphicsItem] = {}
        self._token_radius_px = 42.0
        self._table_grid_margin_px = 42.0
        self._hover_preview_enabled = True
        self._table_background_file = ""
        self.setBackgroundBrush(QBrush(QColor("#dfe5eb")))
        self.selectionChanged.connect(self._emit_selection_changed)

    def apply_visual_settings(
        self,
        *,
        token_radius_px: float | None = None,
        table_grid_margin_px: float | None = None,
        hover_preview_enabled: bool | None = None,
        table_background_file: str | None = None,
    ) -> None:
        if token_radius_px is not None:
            self._token_radius_px = max(16.0, min(180.0, float(token_radius_px)))
        if table_grid_margin_px is not None:
            self._table_grid_margin_px = max(12.0, min(240.0, float(table_grid_margin_px)))
        if hover_preview_enabled is not None:
            self._hover_preview_enabled = bool(hover_preview_enabled)

        if table_background_file is not None:
            self._table_background_file = str(table_background_file)
            bg_path = self._table_background_file.strip()
            if bg_path:
                pixmap = QPixmap(bg_path)
                if not pixmap.isNull():
                    self.setBackgroundBrush(QBrush(pixmap))
                else:
                    self.setBackgroundBrush(QBrush(QColor("#dfe5eb")))
            else:
                self.setBackgroundBrush(QBrush(QColor("#dfe5eb")))

    def token_radius_px(self) -> float:
        return self._token_radius_px

    def table_background_file(self) -> str:
        return self._table_background_file

    def update_viewport_rect(self, width: float, height: float) -> None:
        safe_width = max(120.0, float(width))
        safe_height = max(120.0, float(height))

        current = self.sceneRect()
        if abs(current.width() - safe_width) < 0.1 and abs(current.height() - safe_height) < 0.1:
            return

        self.setSceneRect(0.0, 0.0, safe_width, safe_height)
        self._reposition_items_from_core_coordinates()

    def load_from_session(self, entries: list[tuple[Token, TableToken]]) -> None:
        self._token_items.clear()
        self.clear()

        for token, table_token in entries:
            item = TokenGraphicsItem(
                token=token,
                table_token=table_token,
                size=self._token_radius_px * 2.0,
                hover_preview_enabled=self._hover_preview_enabled,
            )
            pos = self._map_core_coordinates(table_token.x, table_token.y)
            item.setPos(pos)
            item.setRotation(table_token.rotation)
            item.setZValue(table_token.z)
            item.selected.connect(self.token_selected.emit)
            item.flip_requested.connect(self.token_flip_requested.emit)
            item.drag_finished.connect(self._on_item_drag_finished)
            self.addItem(item)
            self._token_items[str(token.id)] = item

    def token_items(self) -> dict[str, TokenGraphicsItem]:
        return dict(self._token_items)

    def set_selected_token_ids(self, token_ids: set[str]) -> None:
        for token_id, item in self._token_items.items():
            item.setSelected(token_id in token_ids)

    def selected_token_ids(self) -> set[str]:
        selected: set[str] = set()
        for token_id, item in self._token_items.items():
            try:
                if item.isSelected():
                    selected.add(token_id)
            except RuntimeError:
                # Item may have been deleted by scene clear during refresh.
                continue
        return selected

    def _map_core_coordinates(self, x: float, y: float) -> QPointF:
        rect = self.sceneRect()
        margin = self._table_grid_margin_px
        width = rect.width() - margin * 2
        height = rect.height() - margin * 2

        px = margin + (x / 100.0) * width
        py = margin + (y / 100.0) * height
        return QPointF(px, py)

    def _map_scene_to_core_coordinates(self, px: float, py: float) -> tuple[float, float]:
        rect = self.sceneRect()
        margin = self._table_grid_margin_px
        width = rect.width() - margin * 2
        height = rect.height() - margin * 2

        if width <= 0 or height <= 0:
            return 50.0, 50.0

        x = ((px - margin) / width) * 100.0
        y = ((py - margin) / height) * 100.0

        x = max(0.0, min(100.0, x))
        y = max(0.0, min(100.0, y))
        return round(x, 3), round(y, 3)

    def _on_item_drag_finished(self, token_id: str, scene_x: float, scene_y: float) -> None:
        x, y = self._map_scene_to_core_coordinates(scene_x, scene_y)
        self.token_dragged.emit(token_id, x, y)

    def _emit_selection_changed(self) -> None:
        self.token_selection_changed.emit(self.selected_token_ids())

    def _reposition_items_from_core_coordinates(self) -> None:
        for item in self._token_items.values():
            table_token = item.table_token
            item.setPos(self._map_core_coordinates(table_token.x, table_token.y))
