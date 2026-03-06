# -*- coding: utf-8 -*-
import os
import tempfile
import hashlib
import shutil
from src.utils.qt_compat import QtCore, QtGui

class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    result_ready = QtCore.Signal(str, object)
    progress = QtCore.Signal(int, str)
    scan_result = QtCore.Signal(dict) 

class ThumbnailLoader(QtCore.QRunnable):
    def __init__(self, asset_data, cache_dir=None):
        super(ThumbnailLoader, self).__init__()
        self.asset_data = asset_data
        self.signals = WorkerSignals()
        self.is_running = True
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "NoobTools_Cache")
        if not os.path.exists(self.cache_dir):
            try: os.makedirs(self.cache_dir)
            except Exception: self.cache_dir = tempfile.gettempdir()

    def get_cache_path(self, asset_path, asset_name):
        try:
            if isinstance(asset_path, bytes): asset_path = asset_path.decode('utf-8', errors='replace')
            if isinstance(asset_name, bytes): asset_name = asset_name.decode('utf-8', errors='replace')
            cache_key = hashlib.md5((asset_path + asset_name).encode('utf-8', errors='replace')).hexdigest()
            return os.path.join(self.cache_dir, "{}.png".format(cache_key))
        except Exception:
            safe_name = "".join(c for c in str(asset_name) if c.isalnum() or c in ('_', '-'))[:50]
            return os.path.join(self.cache_dir, "{}.png".format(safe_name))

    def run(self):
        total = len(self.asset_data)
        for idx, data in enumerate(self.asset_data):
            if not self.is_running: break
            try:
                folder_path = str(data.get('path', ''))
                asset_name = str(data.get('name', 'Unknown'))
                if not folder_path or not os.path.exists(folder_path): continue
                
                cache_path = self.get_cache_path(folder_path, asset_name)
                thumb_path = None

                if cache_path and os.path.exists(cache_path):
                    try:
                        if os.path.getmtime(cache_path) > os.path.getmtime(folder_path):
                            thumb_path = cache_path
                    except Exception: pass

                if not thumb_path:
                    parent_dir = os.path.dirname(folder_path)
                    possible_exts = [".jpg", ".jpeg", ".png", ".bmp", ".tga", ".tif"]
                    for ext in possible_exts:
                        attempt = os.path.join(parent_dir, asset_name + ext)
                        if os.path.exists(attempt): thumb_path = attempt; break
                    
                    if not thumb_path and os.path.isdir(folder_path):
                        try:
                            for entry in os.listdir(folder_path):
                                if entry.lower().endswith(tuple(possible_exts)):
                                    thumb_path = os.path.join(folder_path, entry); break
                        except Exception: pass

                    if thumb_path and cache_path:
                        try: shutil.copy2(thumb_path, cache_path)
                        except Exception: pass

                final_w, final_h = 170, 160
                final_pix = QtGui.QPixmap(final_w, final_h)
                final_pix.fill(QtGui.QColor(30, 30, 30))

                if thumb_path and os.path.exists(thumb_path):
                    pixmap = QtGui.QPixmap(thumb_path)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(final_w, final_h-30, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                        x_pos = (final_w - scaled.width()) // 2
                        painter = QtGui.QPainter(final_pix)
                        painter.drawPixmap(int(x_pos), 0, scaled)
                        painter.end()

                painter = QtGui.QPainter(final_pix)
                painter.setPen(QtGui.QColor(220, 220, 220))
                font = painter.font()
                font.setPointSize(9)
                painter.setFont(font)
                display_name = asset_name[:25] + "..." if len(asset_name) > 25 else asset_name
                text_rect = QtCore.QRect(0, final_h-30, final_w, 30)
                painter.drawText(text_rect, QtCore.Qt.AlignCenter, display_name)
                painter.end()

                self.signals.result_ready.emit(folder_path, QtGui.QIcon(final_pix))
                progress = int((float(idx + 1) / total) * 100)
                self.signals.progress.emit(progress, "Carregando miniaturas... {}%".format(progress))
            except Exception: continue
        self.signals.finished.emit()

    def stop(self): self.is_running = False

class RelinkScannerWorker(QtCore.QRunnable):
    def __init__(self, search_path, include_subfolders):
        super(RelinkScannerWorker, self).__init__()
        self.search_path = search_path
        self.include_subfolders = include_subfolders
        self.signals = WorkerSignals()
        self.is_running = True

    def run(self):
        file_dict = {}
        try:
            for root, dirs, files in os.walk(self.search_path):
                if not self.is_running: break
                
                if not self.include_subfolders and root != self.search_path: 
                    continue
                
                dirs[:] = [d for d in dirs if os.access(os.path.join(root, d), os.R_OK)]
                
                for f in files:
                    try:
                        full_path = os.path.join(root, f)
                        if os.access(full_path, os.R_OK):
                            key = os.path.splitext(f.lower())[0]
                            if key not in file_dict:
                                file_dict[key] = []
                            file_dict[key].append(full_path)
                    except Exception: pass
        except Exception: pass
            
        self.signals.scan_result.emit(file_dict)
        self.signals.finished.emit()

    def stop(self): self.is_running = False
