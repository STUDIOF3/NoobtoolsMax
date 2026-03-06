# -*- coding: utf-8 -*-
from src.utils.qt_compat import QtWidgets, QtCore

class DroppableAssetList(QtWidgets.QListWidget):
    files_dropped = QtCore.Signal(list)
    def __init__(self, parent=None):
        super(DroppableAssetList, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
            if files: self.files_dropped.emit(files)
            event.acceptProposedAction()

class ToastNotification(QtWidgets.QWidget):
    """Widget de notificação flutuante que desaparece sozinho."""
    def __init__(self, parent, message, duration=3000):
        super(ToastNotification, self).__init__(parent)
        self.setObjectName("ToastWidget")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowTransparentForInput)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(message)
        self.label.setObjectName("ToastLabel")
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.label)
        
        # Animação de Fade
        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.animation = QtCore.QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        
        # Timer para fechar
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_and_delete)
        
        self.adjustSize()
        self.show_at_center(parent)

    def show_at_center(self, parent):
        if parent:
            # Pegar coordenadas globais do pai
            p_pos = parent.mapToGlobal(QtCore.QPoint(0, 0))
            p_width = parent.width()
            p_height = parent.height()
            
            x = p_pos.x() + (p_width - self.width()) // 2
            y = p_pos.y() + p_height - self.height() - 80
            self.move(x, y)
        self.animation.start()
        self.timer.start(3000)

    def hide_and_delete(self):
        self.animation.setDirection(QtCore.QPropertyAnimation.Backward)
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()
