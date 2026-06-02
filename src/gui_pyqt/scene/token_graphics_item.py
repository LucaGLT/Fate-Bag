import math
from pathlib import Path
from uuid import UUID

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget

from src.core.models.enums import TokenFrontType, TokenShape, TokenState
from src.core.models.table_token import TableToken
from src.core.models.token import Token


class TokenGraphicsItem(QGraphicsObject):
    clicked = pyqtSignal(str)

    def __init__(self, token: Token, table_token: TableToken, size: float = 84.0) -> None:
        super().__init__()
        self.token = token
        self.table_token = table_token
        self.size = size
        self._bounds = QRectF(-size / 2, -size / 2, size, size)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)

    def boundingRect(self) -> QRectF:
        return self._bounds

    def paint(
        self,
        painter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget

        path = self._shape_path()
        painter.setRenderHint(painter.RenderHint.Antialiasing, True)

        painter.setPen(QPen(QColor("#2f3a4a"), 2))
        painter.setBrush(QBrush(self._base_color()))
        painter.drawPath(path)

        if self.table_token.state == TokenState.FACE_DOWN:
            self._draw_back(painter, path)
        else:
            self._draw_front(painter, path)

        if self.isSelected():
            painter.setPen(QPen(QColor("#ffcc00"), 3, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(str(self.token.id))
        super().mousePressEvent(event)

    def _shape_path(self) -> QPainterPath:
        path = QPainterPath()
        if self.token.shape == TokenShape.CIRCLE:
            path.addEllipse(self._bounds)
            return path

        radius = self.size / 2
        points = []
        for i in range(6):
            angle_deg = 60 * i - 30
            angle_rad = math.radians(angle_deg)
            x = radius * 0.95 * math.cos(angle_rad)
            y = radius * 0.95 * math.sin(angle_rad)
            points.append((x, y))

        polygon = QPolygonF()
        for x, y in points:
            polygon.append(QPointF(x, y))
        path.addPolygon(polygon)
        path.closeSubpath()
        return path

    def _base_color(self) -> QColor:
        if self.table_token.state == TokenState.FACE_DOWN:
            return QColor("#4f5d75")
        if self.table_token.state == TokenState.FACE_UP:
            return QColor("#f0f4f8")
        if self.table_token.state == TokenState.LOCKED:
            return QColor("#8f95a3")
        if self.table_token.state == TokenState.EXCLUDED:
            return QColor("#b73e3e")
        return QColor("#f0f4f8")

    def _draw_back(self, painter, clip_path: QPainterPath) -> None:
        back_path = Path(self.token.back_value)
        if back_path.is_file():
            pixmap = QPixmap(str(back_path))
            if not pixmap.isNull():
                painter.save()
                painter.setClipPath(clip_path)
                painter.drawPixmap(self._bounds.toRect(), pixmap)
                painter.restore()
                return

        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(self._bounds, Qt.AlignmentFlag.AlignCenter, "BACK")

    def _draw_front(self, painter, clip_path: QPainterPath) -> None:
        if self.token.front_type == TokenFrontType.IMAGE:
            front_path = Path(self.token.front_value)
            if front_path.is_file():
                pixmap = QPixmap(str(front_path))
                if not pixmap.isNull():
                    painter.save()
                    painter.setClipPath(clip_path)
                    painter.drawPixmap(self._bounds.toRect(), pixmap)
                    painter.restore()
                    return

        painter.setPen(QPen(QColor("#1f2a36"), 1))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(self._bounds.adjusted(6, 6, -6, -6), Qt.AlignmentFlag.AlignCenter, self.token.front_value)

    @property
    def token_id(self) -> UUID:
        return self.token.id
