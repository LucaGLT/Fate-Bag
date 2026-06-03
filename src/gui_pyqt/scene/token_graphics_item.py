import math
import html
import re
from pathlib import Path
from typing import Callable
from uuid import UUID

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QTextDocument,
    QTextOption,
)
from PyQt6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget

from src.core.models.enums import TokenFrontType, TokenShape, TokenState
from src.core.models.table_token import TableToken
from src.core.models.token import Token


class TokenGraphicsItem(QGraphicsObject):
    selected = pyqtSignal(str)
    flip_requested = pyqtSignal(str)
    drag_finished = pyqtSignal(str, float, float)

    def __init__(
        self,
        token: Token,
        table_token: TableToken,
        size: float = 84.0,
        *,
        hover_preview_enabled: bool = True,
        front_text_font_px: int = 7,
        tip_text_font_px: int = 8,
    ) -> None:
        super().__init__()
        self.token = token
        self.table_token = table_token
        self.size = size
        self._hover_preview_enabled = bool(hover_preview_enabled)
        self._front_text_font_px = max(5, min(24, int(front_text_font_px)))
        self._tip_text_font_px = max(6, min(28, int(tip_text_font_px)))
        self._bounds = QRectF(-size / 2, -size / 2, size, size)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)
        self._press_pos = QPointF(0.0, 0.0)
        self._hover_preview_active = False
        self._flip_scale_x = 1.0
        self._is_flip_animating = False
        self._flip_animation_group: QSequentialAnimationGroup | None = None

    def boundingRect(self) -> QRectF:
        rect = QRectF(self._bounds)
        overlay_rect = self._tip_overlay_rect()
        if overlay_rect is not None:
            rect = rect.united(overlay_rect)
        return rect

    def paint(
        self,
        painter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget

        painter.save()
        painter.scale(self._flip_scale_x, 1.0)

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

        painter.restore()

        self._draw_tip_overlay(painter)

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

    def hoverEnterEvent(self, event) -> None:
        self._set_hover_preview_enabled(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._set_hover_preview_enabled(False)
        super().hoverLeaveEvent(event)

    def _set_hover_preview_enabled(self, enabled: bool) -> None:
        next_state = bool(enabled)
        if self._hover_preview_active == next_state:
            return
        self.prepareGeometryChange()
        self._hover_preview_active = next_state
        self.update()

    def start_flip_animation(
        self,
        *,
        on_half_flip: Callable[[], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        duration_ms: int = 220,
    ) -> bool:
        if self._is_flip_animating:
            return False

        self._is_flip_animating = True
        self._flip_scale_x = 1.0
        self.update()

        close_anim = QPropertyAnimation(self, b"flipScaleX")
        close_anim.setDuration(max(40, duration_ms // 2))
        close_anim.setStartValue(1.0)
        close_anim.setEndValue(0.08)
        close_anim.setEasingCurve(QEasingCurve.Type.InCubic)

        open_anim = QPropertyAnimation(self, b"flipScaleX")
        open_anim.setDuration(max(40, duration_ms // 2))
        open_anim.setStartValue(0.08)
        open_anim.setEndValue(1.0)
        open_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        sequence = QSequentialAnimationGroup(self)
        sequence.addAnimation(close_anim)
        sequence.addAnimation(open_anim)

        half_called = {"value": False}

        def _on_half() -> None:
            if half_called["value"]:
                return
            half_called["value"] = True
            if on_half_flip is not None:
                on_half_flip()

        close_anim.finished.connect(_on_half)

        def _on_done() -> None:
            self._flip_scale_x = 1.0
            self._is_flip_animating = False
            self._flip_animation_group = None
            self.update()
            if on_finished is not None:
                on_finished()

        sequence.finished.connect(_on_done)
        self._flip_animation_group = sequence
        sequence.start()
        return True

    def is_flip_animating(self) -> bool:
        return self._is_flip_animating

    def _get_flip_scale_x(self) -> float:
        return self._flip_scale_x

    def _set_flip_scale_x(self, value: float) -> None:
        bounded = max(0.05, min(1.0, float(value)))
        if abs(self._flip_scale_x - bounded) < 0.001:
            return
        self._flip_scale_x = bounded
        self.update()

    flipScaleX = pyqtProperty(float, fget=_get_flip_scale_x, fset=_set_flip_scale_x)

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
        effective_front_type = self._effective_front_type()

        front_pixmap: QPixmap | None = None
        if effective_front_type in (TokenFrontType.IMAGE, TokenFrontType.TEXT_IMAGE):
            front_path = Path(self.token.front_value)
            if front_path.is_file():
                pixmap = QPixmap(str(front_path))
                if not pixmap.isNull():
                    front_pixmap = pixmap
                    painter.save()
                    painter.setClipPath(clip_path)
                    painter.drawPixmap(self._bounds.toRect(), pixmap)
                    painter.restore()
                    if effective_front_type == TokenFrontType.IMAGE:
                        return

        front_label = self._front_label_text(effective_front_type)
        if not front_label:
            return

        if effective_front_type == TokenFrontType.TEXT_IMAGE:
            color_mode = str(self.token.metadata.get("front_text_color_mode", "auto")).strip().lower()
            if color_mode == "black":
                text_color = "#000000"
            elif color_mode == "white":
                text_color = "#ffffff"
            else:
                text_color = self._auto_text_color_for_pixmap(front_pixmap)
        else:
            text_color = "#1f2a36"

        self._draw_formatted_front_text(painter, front_label, text_color)

    def _effective_front_type(self) -> TokenFrontType:
        if not self._hover_preview_enabled or not self._hover_preview_active:
            return self.token.front_type

        if self.token.front_type == TokenFrontType.TEXT:
            if self._has_front_image():
                return TokenFrontType.IMAGE
            return TokenFrontType.TEXT

        if self.token.front_type == TokenFrontType.IMAGE:
            return TokenFrontType.TEXT

        return self.token.front_type

    def _front_label_text(self, front_type: TokenFrontType) -> str:
        if front_type == TokenFrontType.TEXT:
            if self.token.front_type == TokenFrontType.TEXT:
                return self.token.front_value.replace("|", "\n")
            return self._fallback_front_text().replace("|", "\n")
        if front_type == TokenFrontType.TEXT_IMAGE:
            return str(self.token.metadata.get("front_text", "")).strip().replace("|", "\n")
        return ""

    def _has_front_image(self) -> bool:
        return Path(self.token.front_value).is_file()

    def _fallback_front_text(self) -> str:
        text = str(self.token.metadata.get("front_text", "")).strip()
        if text:
            return text
        return self.token.name

    def _tip_text(self) -> str:
        return str(self.token.metadata.get("tip_text", "")).strip()

    def _tip_overlay_rect(self) -> QRectF | None:
        if not self._hover_preview_enabled or not self._hover_preview_active:
            return None

        tip_text = self._tip_text()
        if not tip_text:
            return None

        document = self._create_text_document(
            tip_text,
            color="#f4f7fb",
            width=max(180.0, self.size * 2.75),
            font_px=self._tip_text_font_px,
        )
        document_height = document.size().height()
        width = document.textWidth() + 20.0
        height = document_height + 50
        top = self._bounds.bottom() + 8.0
        left = -width / 2.0
        return QRectF(left, top, width, height)

    def _draw_tip_overlay(self, painter) -> None:
        overlay_rect = self._tip_overlay_rect()
        if overlay_rect is None:
            return

        tip_text = self._tip_text().replace("|", "\n")
        inner_rect = overlay_rect.adjusted(10.0, 9.0, -10.0, -9.0)
        document = self._create_text_document(
            tip_text,
            color="#f4f7fb",
            width=inner_rect.width(),
            font_px=self._tip_text_font_px,
        )
        vertical_offset = max(0.0, (inner_rect.height() - document.size().height()) / 2.0)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor(24, 31, 40, 220), 1.2))
        painter.setBrush(QBrush(QColor(20, 27, 35, 228)))
        painter.drawRoundedRect(overlay_rect, 10.0, 10.0)
        painter.translate(inner_rect.left(), inner_rect.top() + vertical_offset)
        document.drawContents(painter)
        painter.restore()

    def _draw_formatted_front_text(self, painter, text: str, color: str) -> None:
        rect = self._bounds.adjusted(6, 6, -6, -6)
        document = self._create_text_document(text, color=color, width=rect.width(), font_px=self._front_text_font_px)

        vertical_offset = max(0.0, (rect.height() - document.size().height()) / 2.0)

        painter.save()
        painter.translate(rect.left(), rect.top() + vertical_offset)
        document.drawContents(painter)
        painter.restore()

    @classmethod
    def _create_text_document(cls, text: str, *, color: str, width: float, font_px: int) -> QTextDocument:
        title_font_px = max(1, int(font_px) + 2)
        rich_text = cls._to_rich_text(text, color, title_font_px=title_font_px)
        document = QTextDocument()
        document.setDocumentMargin(0)
        point_size = max(1, int(round(font_px * 0.75)))
        document.setDefaultFont(QFont("Segoe UI", point_size, QFont.Weight.DemiBold))
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WordWrap)
        option.setAlignment(Qt.AlignmentFlag.AlignCenter)
        document.setDefaultTextOption(option)
        document.setHtml(rich_text)
        document.setTextWidth(width)
        return document

    @staticmethod
    def _to_rich_text(text: str, color: str, *, title_font_px: int) -> str:
        escaped = html.escape(text)
        escaped = escaped.replace("\n", "<br/>")

        escaped = re.sub(
            r"&lt;\s*([^&<>]+?)\s*&gt;",
            rf'<span style="font-size:{title_font_px}px; font-weight:700;"><b>\1</b></span>',
            escaped,
        )
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)

        return f'<div style="color:{color};">{escaped}</div>'

    @staticmethod
    def _auto_text_color_for_pixmap(pixmap: QPixmap | None) -> str:
        if pixmap is None or pixmap.isNull():
            return "#1f2a36"

        image = pixmap.toImage().scaled(
            1,
            1,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        color = image.pixelColor(0, 0)
        luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
        return "#000000" if luminance >= 145 else "#ffffff"

    @property
    def token_id(self) -> UUID:
        return self.token.id
