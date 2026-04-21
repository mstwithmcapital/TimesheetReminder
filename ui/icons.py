from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap


def make_app_icon() -> QIcon:
    """Generate the application clock icon used in the tray, main window, and dialogs."""
    px = QPixmap(64, 64)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#1565c0"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, 64, 64)
    p.setBrush(QColor("white"))
    p.drawEllipse(6, 6, 52, 52)
    p.setPen(QColor("#1565c0"))
    from PyQt5.QtCore import QPoint
    p.drawLine(QPoint(32, 32), QPoint(32, 14))
    p.drawLine(QPoint(32, 32), QPoint(46, 32))
    p.end()
    return QIcon(px)
