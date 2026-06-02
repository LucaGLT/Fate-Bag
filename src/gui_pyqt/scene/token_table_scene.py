from PyQt6.QtCore import QPointF, pyqtSignal
from PyQt6.QtWidgets import QGraphicsScene

from src.core.models.table_token import TableToken
from src.core.models.token import Token
from src.gui_pyqt.scene.token_graphics_item import TokenGraphicsItem


class TokenTableScene(QGraphicsScene):
    token_flip_requested = pyqtSignal(str)

    def __init__(self, scene_width: float = 1200.0, scene_height: float = 760.0) -> None:
        super().__init__(0, 0, scene_width, scene_height)
        self._token_items: dict[str, TokenGraphicsItem] = {}

    def load_from_session(self, entries: list[tuple[Token, TableToken]]) -> None:
        self.clear()
        self._token_items.clear()

        for token, table_token in entries:
            item = TokenGraphicsItem(token=token, table_token=table_token)
            pos = self._map_core_coordinates(table_token.x, table_token.y)
            item.setPos(pos)
            item.setRotation(table_token.rotation)
            item.setZValue(table_token.z)
            item.clicked.connect(self.token_flip_requested.emit)
            self.addItem(item)
            self._token_items[str(token.id)] = item

    def token_items(self) -> dict[str, TokenGraphicsItem]:
        return dict(self._token_items)

    def _map_core_coordinates(self, x: float, y: float) -> QPointF:
        rect = self.sceneRect()
        margin = 42.0
        width = rect.width() - margin * 2
        height = rect.height() - margin * 2

        px = margin + (x / 100.0) * width
        py = margin + (y / 100.0) * height
        return QPointF(px, py)
