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
    selected = pyqtSignal(str)
    flip_requested = pyqtSignal(str)
    drag_finished = pyqtSignal(str, float, float)

    def __init__(self, token: Token, table_token: TableToken, size: float = 84.0) -> None:
        super().__init__()
        self.token = token
        self.table_token = table_token
        self.size = size
        self._bounds = QRectF(-size / 2, -size / 2, size, size)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self._press_pos = QPointF(0.0, 0.0)

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
        self._press_pos = QPointF(self.pos())
        is_ctrl_click = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        super().mousePressEvent(event)
        if not is_ctrl_click:
            self.selected.emit(str(self.token.id))

    def mouseDoubleClickEvent(self, event) -> None:
        super().mouseDoubleClickEvent(event)
        self.selected.emit(str(self.token.id))
        self.flip_requested.emit(str(self.token.id))

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        current = self.pos()
        delta = current - self._press_pos
        moved = abs(delta.x()) > 0.5 or abs(delta.y()) > 0.5
        if moved:
            self.selected.emit(str(self.token.id))
            self.drag_finished.emit(str(self.token.id), float(current.x()), float(current.y()))

    def _shape_path(self) -> QPainterPath:
        path = QPainterPath()
        if self.token.shape == TokenShape.CIRCLE:
            path.addEllipse(self._bounds)
            return path

        if self.token.shape == TokenShape.SQUARE:
            return self._rectangle_path(1.0, 1.0)

        if self.token.shape == TokenShape.PENTAGON:
            return self._regular_polygon_path(5)

        if self.token.shape == TokenShape.EPTAGON:
            return self._regular_polygon_path(7)

        if self.token.shape == TokenShape.HEXAGON:
            return self._regular_polygon_path(6)

        if self.token.shape == TokenShape.OCTAGON:
            return self._regular_polygon_path(8)

        if self.token.shape == TokenShape.STAR:
            return self._star_path()

        if self.token.shape == TokenShape.RECTANGLE_3_4:
            return self._rectangle_path(3.0, 4.0)

        if self.token.shape == TokenShape.RECTANGLE_4_3:
            return self._rectangle_path(4.0, 3.0)

        if self.token.shape == TokenShape.RECTANGLE_3_5:
            return self._rectangle_path(3.0, 5.0)

        if self.token.shape == TokenShape.RECTANGLE_5_3:
            return self._rectangle_path(5.0, 3.0)

        return self._regular_polygon_path(6)

    def _regular_polygon_path(self, sides: int, rotation_deg: float = -90.0) -> QPainterPath:
        path = QPainterPath()
        radius = (self.size / 2) * 0.95
        polygon = QPolygonF()

        for i in range(sides):
            angle_deg = (360.0 / sides) * i + rotation_deg
            angle_rad = math.radians(angle_deg)
            polygon.append(QPointF(radius * math.cos(angle_rad), radius * math.sin(angle_rad)))

        path.addPolygon(polygon)
        path.closeSubpath()
        return path

    def _star_path(self) -> QPainterPath:
        path = QPainterPath()
        outer_radius = (self.size / 2) * 0.95
        inner_radius = outer_radius * 0.45
        polygon = QPolygonF()

        for i in range(10):
            radius = outer_radius if i % 2 == 0 else inner_radius
            angle_deg = i * 36.0 - 90.0
            angle_rad = math.radians(angle_deg)
            polygon.append(QPointF(radius * math.cos(angle_rad), radius * math.sin(angle_rad)))

        path.addPolygon(polygon)
        path.closeSubpath()
        return path

    def _rectangle_path(self, aspect_w: float, aspect_h: float) -> QPainterPath:
        path = QPainterPath()
        max_width = self._bounds.width() * 0.95
        max_height = self._bounds.height() * 0.95
        ratio = aspect_w / aspect_h

        if max_width / max_height > ratio:
            height = max_height
            width = height * ratio
        else:
            width = max_width
            height = width / ratio

        rect = QRectF(-width / 2, -height / 2, width, height)
        path.addRect(rect)
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
        if self.token.front_type in (TokenFrontType.IMAGE, TokenFrontType.TEXT_IMAGE):
            front_path = Path(self.token.front_value)
            if front_path.is_file():
                pixmap = QPixmap(str(front_path))
                if not pixmap.isNull():
                    painter.save()
                    painter.setClipPath(clip_path)
                    painter.drawPixmap(self._bounds.toRect(), pixmap)
                    painter.restore()
                    if self.token.front_type == TokenFrontType.IMAGE:
                        return

        front_label = self._front_label_text()
        if not front_label:
            return

        if self.token.front_type == TokenFrontType.TEXT_IMAGE:
            # Improve legibility of overlay text over front images.
            painter.save()
            overlay = QColor(0, 0, 0, 120)
            painter.setBrush(QBrush(overlay))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(self._bounds.adjusted(6, self._bounds.height() * 0.25, -6, -6))
            painter.restore()
            painter.setPen(QPen(QColor("#ffffff"), 1))
        else:
            painter.setPen(QPen(QColor("#1f2a36"), 1))

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(self._bounds.adjusted(6, 6, -6, -6), Qt.AlignmentFlag.AlignCenter, front_label)

    def _front_label_text(self) -> str:
        if self.token.front_type == TokenFrontType.TEXT:
            return self.token.front_value
        if self.token.front_type == TokenFrontType.TEXT_IMAGE:
            return str(self.token.metadata.get("front_text", "")).strip()
        return ""

    @property
    def token_id(self) -> UUID:
        return self.token.id
