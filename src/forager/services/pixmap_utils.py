from __future__ import annotations
import io
from PySide6.QtCore import Qt, QByteArray
from PySide6.QtGui import QPixmap, QImage


def bytes_to_pixmap(data: bytes, max_size: int = 0) -> QPixmap | None:
    if not data:
        return None
    pix = QPixmap()
    if pix.loadFromData(QByteArray(data)):
        if max_size > 0 and (pix.width() > max_size or pix.height() > max_size):
            pix = pix.scaled(
                max_size, max_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pix
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGBA")
        if max_size > 0:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        raw = img.tobytes("raw", "RGBA")
        qimg = QImage(raw, img.width, img.height, QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimg)
    except Exception:
        return None


def scale_crop(source: QPixmap, width: int, height: int) -> QPixmap:
    if source.isNull():
        return source
    scaled = source.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = (scaled.width() - width) // 2
    y = (scaled.height() - height) // 2
    return scaled.copy(x, y, width, height)


def scaled(source: QPixmap, width: int, height: int) -> QPixmap:
    if source.isNull():
        return source
    return source.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
