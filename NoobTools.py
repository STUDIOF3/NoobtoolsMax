# -*- coding: utf-8 -*-
import sys
import os
import glob
import logging
import tempfile
import time
import json
import hashlib
import shutil
from datetime import datetime
from functools import partial

# ==============================================================================
# 0. COMPATIBILIDADE UNIVERSAL (MAX 2020-2025+)
# ==============================================================================
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    IS_PYSIDE6 = True
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        IS_PYSIDE6 = False
    except ImportError:
        from PySide import QtWidgets, QtCore, QtGui
        IS_PYSIDE6 = False

def qt_exec(obj, *args):
    """Função helper para compatibilidade entre PySide2 e PySide6"""
    if hasattr(obj, 'exec') and callable(getattr(obj, 'exec', None)):
        return obj.exec(*args)
    elif hasattr(obj, 'exec_') and callable(getattr(obj, 'exec_', None)):
        return obj.exec_(*args)
    elif hasattr(obj, 'show'):
        obj.show()
        return None
    return None

import pymxs

# ==============================================================================
# 1. LOGGING SIMPLES E ROBUSTO
# ==============================================================================
LOG_FILE = os.path.join(tempfile.gettempdir(), "NoobTools_Log.txt")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_info(msg):
    try:
        if isinstance(msg, bytes): msg = msg.decode('utf-8', errors='replace')
        msg = str(msg)
        logging.info(msg)
        print("[NoobTools] {}".format(msg))
    except Exception as e:
        pass

def log_error(msg):
    try:
        if isinstance(msg, bytes): msg = msg.decode('utf-8', errors='replace')
        msg = str(msg)
        logging.error(msg)
        print("[NoobTools Error] {}".format(msg))
    except Exception as e:
        pass

def log_warning(msg):
    try:
        if isinstance(msg, bytes): msg = msg.decode('utf-8', errors='replace')
        msg = str(msg)
        logging.warning(msg)
        print("[NoobTools Warning] {}".format(msg))
    except Exception as e:
        pass

# ==============================================================================
# 2. LÓGICA MAXSCRIPT UNIFICADA
# ==============================================================================
MAXSCRIPT_LOGIC = r"""
fn global_getSupportedMapClasses = 
(
    local types = #(
        #(BitmapTexture, "filename"),
        #(VRayBitmap, "HDRIMapName"),
        #(VRayBitmap, "filename"),
        #(CoronaBitmap, "filename"),
        #(ai_Image, "filename"),
        #(OSLMap, "filename"),
        #(PhysicalMaterial, "base_color"),
        #(Redshift_Bitmap, "filename"),
        #(FStormBitmap, "filename"),
        #(FStormTexture, "filename")
    )
    return types
)

fn global_guessRenderer filepath = (
    local ext = getFilenameType filepath
    if (toLower ext) != ".max" do return "N/A"
    
    local isVRay = false
    local isCorona = false
    local isFStorm = false
    local isArnold = false
    
    try (
        local meta = getMAXFileAssetMetadata filepath
        if meta != undefined do (
            for m in meta do (
                try (
                    local cName = m.className as string
                    if matchPattern cName pattern:"*VRay*" do isVRay = true
                    if matchPattern cName pattern:"*Corona*" do isCorona = true
                    if matchPattern cName pattern:"*FStorm*" do isFStorm = true
                    if matchPattern cName pattern:"*Arnold*" do isArnold = true
                ) catch()
            )
        )
    ) catch()
    
    local lowPath = toLower filepath
    if not isVRay and (matchPattern lowPath pattern:"*vray*" or matchPattern lowPath pattern:"*v-ray*") do isVRay = true
    if not isCorona and (matchPattern lowPath pattern:"*corona*") do isCorona = true
    if not isFStorm and (matchPattern lowPath pattern:"*fstorm*") do isFStorm = true
    
    if isVRay and isCorona do return "V-Ray & Corona"
    if isVRay do return "V-Ray"
    if isCorona do return "Corona Render"
    if isFStorm do return "FStorm"
    if isArnold do return "Arnold"
    return "Unknown"
)

fn global_selectObjectsFromMissing pathString = 
(
    if pathString == undefined or pathString == "" do return false
    local foundMats = #()
    local types = global_getSupportedMapClasses()
    for t in types do (
        try (
            local instances = getClassInstances t[1]
            for m in instances do (
                if isProperty m t[2] do (
                    local val = getProperty m t[2]
                    if val == pathString do appendIfUnique foundMats m
                )
            )
        ) catch()
    )
    local finalObjs = #()
    for m in foundMats do (
        local deps = refs.dependents m
        for d in deps do (
            if isValidNode d and not isDeleted d do appendIfUnique finalObjs d
        )
    )
    if finalObjs.count > 0 then (
        clearSelection()
        select finalObjs
        redrawViews()
        return finalObjs.count
    ) else (
        return 0
    )
)

fn global_convertToUNC = 
(
    local count = 0
    local types = global_getSupportedMapClasses()
    for t in types do (
        try (
            local instances = getClassInstances t[1]
            for m in instances do (
                if isProperty m t[2] do (
                    local val = getProperty m t[2]
                    if val != undefined and val != "" and (matchPattern val pattern:"*:") do (
                        local unc = pathConfig.convertPathToUnc val
                        if unc != undefined and unc != val do (
                            setProperty m t[2] unc
                            count += 1
                        )
                    )
                )
            )
        ) catch()
    )
    return count
)

fn global_stripMissingPaths missingList = 
(
    local count = 0
    local types = global_getSupportedMapClasses()
    for t in types do (
        try (
            local maps = getClassInstances t[1]
            for m in maps do (
                if isProperty m t[2] do (
                    local val = getProperty m t[2]
                    if (findItem missingList val) > 0 and (not doesFileExist val) do (
                        setProperty m t[2] ""
                        count += 1
                    )
                )
            )
        ) catch()
    )
    return count
)

fn global_getMissingAssets =
(
    local mList = #()
    if (classOf ATSOps) != undefined do (
        try (
            ATSOps.Refresh()
            local allAssets = #()
            ATSOps.GetFiles &allAssets
            for f in allAssets do (
                if f != undefined and f != "" do (
                    local statusArray = ATSOps.GetFileSystemStatus f
                    local isMissing = false
                    if statusArray != undefined do (
                        for s in statusArray do if s == #missing do isMissing = true
                    )
                    if not isMissing and not (doesFileExist f) do isMissing = true
                    if isMissing do appendIfUnique mList f
                )
            )
        ) catch()
    )
    return mList
)

fn global_collectFiles targetDir = 
(
    local count = 0
    local types = global_getSupportedMapClasses()
    if not (doesDirectoryExist targetDir) do makeDir targetDir
    for t in types do (
        try (
            local instances = getClassInstances t[1]
            for m in instances do (
                if isProperty m t[2] do (
                    local originalPath = getProperty m t[2]
                    if originalPath != undefined and originalPath != "" and (doesFileExist originalPath) do (
                        local fName = filenameFromPath originalPath
                        local newPath = targetDir + "\\" + fName
                        if (copyFile originalPath newPath) or (doesFileExist newPath) do (
                            setProperty m t[2] newPath
                            count += 1
                        )
                    )
                )
            )
        ) catch()
    )
    return count
)

fn global_forcePivotToBottom o = (
    if isValidNode o do (
        local bb = nodeGetBoundingBox o (matrix3 1)
        local bmin = bb[1]; local bmax = bb[2]
        o.pivot = [(bmin.x + bmax.x) / 2.0, (bmin.y + bmax.y) / 2.0, bmin.z]
    )
)

fn global_addSelectionToLayer layerName = (
    local layerObj = LayerManager.getLayerFromName layerName
    if layerObj == undefined do layerObj = LayerManager.newLayerFromName layerName
    layerObj.addNodes selection
    OK
)

fn global_renameSelection prefix suffix = (
    for o in selection do o.name = prefix + o.name + suffix
    OK
)
"""

try:
    pymxs.runtime.execute(MAXSCRIPT_LOGIC)
except Exception as e:
    log_error("Erro na inicialização do MaxScript: {}".format(str(e)))

# ==============================================================================
# 3. THREADING & WORKERS
# ==============================================================================
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

# ==============================================================================
# 4. WIDGET PERSONALIZADO
# ==============================================================================
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

# ==============================================================================
# 5. ESTILO VISUAL MODERNO (Refinado para Hitbox total e Scrollbars)
# ==============================================================================
MODERN_THEME_STYLESHEET = """
QWidget { 
    background-color: #1e1e20; 
    color: #e0e0e0; 
    font-family: "Segoe UI", sans-serif; 
    font-size: 11px; 
}

QGroupBox { 
    border: 1px solid #333337; 
    border-radius: 6px; 
    margin-top: 12px; 
    padding-top: 15px; 
    font-weight: bold; 
    color: #888888; 
    background-color: #242426; 
}

QGroupBox::title { 
    subcontrol-origin: margin; 
    subcontrol-position: top left; 
    padding: 0 5px; 
    left: 10px; 
    background-color: #242426; 
}

/* Base QPushButton - O segredo do hitbox completo está no min-height e ausência de padding vertical */
QPushButton { 
    background-color: #38383c; 
    border: 1px solid #4a4a4e; 
    border-radius: 4px; 
    color: #ffffff; 
    min-height: 26px; 
    padding: 0px 15px; 
    text-align: center;
    outline: none;
    qproperty-cursor: pointingHand; /* Mostra a mãozinha! */
}

QPushButton:hover { 
    background-color: #48484c; 
    border: 1px solid #007acc; 
}

QPushButton:pressed { 
    background-color: #007acc; 
    border: 1px solid #005f9e; 
}

QPushButton:checked { 
    background-color: #007acc; 
    border: 1px solid #005f9e; 
    color: white; 
    font-weight: bold; 
}

QPushButton:disabled { 
    background-color: #2a2a2c; 
    color: #666666; 
    border: 1px solid #333333; 
}

/* Botões Especiais */
QPushButton#btnImport { 
    background-color: #007acc; 
    color: white; 
    font-weight: bold; 
    font-size: 14px; 
    min-height: 42px; /* Garante área de clique massiva */
    border-radius: 6px; 
    border: none; 
}
QPushButton#btnImport:hover { background-color: #008be6; }
QPushButton#btnImport:disabled { background-color: #2a2a2c; color: #555; }

QPushButton#btnRelink { background-color: #5a8a5a; font-weight: bold; font-size: 12px; min-height: 32px; }
QPushButton#btnRelink:hover { background-color: #6a9a6a; }

QPushButton#btnStrip { background-color: #a84a4a; font-weight: bold; min-height: 28px; }
QPushButton#btnStrip:hover { background-color: #b85a5a; }

QPushButton#btnUNC { background-color: #4a6a8a; font-weight: bold; min-height: 28px; }
QPushButton#btnUNC:hover { background-color: #5a7a9a; }

QPushButton#btnScan { background-color: #d67b22; font-weight: bold; min-height: 32px; }
QPushButton#btnScan:hover { background-color: #e68b32; }

/* Entradas de Texto e Comboboxes */
QLineEdit, QComboBox { 
    background-color: #18181a; 
    border: 1px solid #3e3e42; 
    border-radius: 4px; 
    padding: 6px; 
    color: white; 
    min-height: 18px;
}

/* Scrollbars Customizadas e Modernas */
QScrollBar:vertical {
    border: none;
    background-color: #18181a;
    width: 10px;
    margin: 0px 0px 0px 0px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background-color: #4a4a4e;
    min-height: 30px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background-color: #6a6a6e;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    border: none;
    background-color: #18181a;
    height: 10px;
    margin: 0px 0px 0px 0px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background-color: #4a4a4e;
    min-width: 30px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #6a6a6e;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Listas e Tabelas */
QListWidget { 
    background-color: #18181a; 
    border: 1px solid #333337; 
    border-radius: 6px; 
    padding: 5px; 
    outline: none; 
}
QListWidget::item { background-color: #252528; border-radius: 4px; margin: 2px; }
QListWidget::item:selected { background-color: #3a3a40; border: 1px solid #007acc; }
QListWidget::item:hover { background-color: #303035; border: 1px solid #555; }

QTableWidget { background-color: #18181a; border: 1px solid #333337; border-radius: 6px; color: #e0e0e0; outline: none; }
QTableWidget::item:selected { background-color: #333337; border: 1px solid #007acc; }
QHeaderView::section { background-color: #2a2a2c; color: #888; padding: 6px; border: 1px solid #333337; font-weight: bold; }

/* Barra de Progresso Sólida (Líquida) */
QProgressBar { 
    border: 1px solid #333337; 
    border-radius: 6px; 
    background-color: #18181a; 
    text-align: center; 
    color: white; 
    font-weight: bold; 
    min-height: 22px; 
}
QProgressBar::chunk { 
    background-color: #007acc; 
    border-radius: 5px; 
}
QProgressBar#pbRelink::chunk { 
    background-color: #5a8a5a; 
}

/* Checkboxes Visíveis */
QCheckBox {
    spacing: 8px;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    background-color: #18181a;
    border: 1px solid #555555;
    border-radius: 4px;
}
QCheckBox::indicator:hover {
    border: 1px solid #007acc;
}
QCheckBox::indicator:checked {
    background-color: #007acc;
    border: 1px solid #005f9e;
}

/* Menus e Tabs */
QMenu { background-color: #252528; border: 1px solid #444; padding: 5px; border-radius: 4px; }
QMenu::item { padding: 6px 25px; color: #e0e0e0; border-radius: 3px; }
QMenu::item:selected { background-color: #007acc; color: white; }

QTabWidget::pane { border: 1px solid #333337; background-color: #1e1e20; border-radius: 6px; top: -1px; }
QTabBar::tab { background-color: #2a2a2c; color: #888; padding: 10px 18px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: 1px solid #333337; border-bottom: none; }
QTabBar::tab:selected { background-color: #1e1e20; color: #007acc; font-weight: bold; border-bottom: 1px solid #1e1e20; }
QTabBar::tab:hover:!selected { background-color: #38383c; }

QLabel#lblHelp { color: #666; font-style: italic; font-size: 10px; }
"""

def get_max_main_window():
    try:
        app = QtWidgets.QApplication.instance()
        if not app: return None
        try: import qtmax; return qtmax.GetQMaxMainWindow()
        except Exception: pass
        try: import MaxPlus; return MaxPlus.GetQMaxMainWindow()
        except Exception: pass
        for w in app.topLevelWidgets():
            if isinstance(w, QtWidgets.QMainWindow) and ('3ds Max' in w.windowTitle() or 'Autodesk' in w.windowTitle()): return w
        return app.activeWindow()
    except Exception: return None

def add_bitmap_path(path):
    rt = pymxs.runtime
    try:
        current = list(rt.bitmapPaths.getPaths())
        if path not in current:
            rt.bitmapPaths.add(path)
            return True
    except AttributeError:
        try:
            rt.pathConfig.appendPathToBitmaps(path)
            return True
        except Exception: pass
    return False

def setup_bitmap_paths_for_asset(asset_folder):
    added = []
    if add_bitmap_path(asset_folder): added.append(asset_folder)
    for sub in ['maps', 'textures', 'tex']:
        subpath = os.path.join(asset_folder, sub)
        if os.path.isdir(subpath) and add_bitmap_path(subpath):
            added.append(subpath)
    return added

def refresh_asset_tracker():
    try: pymxs.runtime.ATSOps.Refresh()
    except Exception: pass

# ==============================================================================
# 6. JANELA PRINCIPAL
# ==============================================================================
class NoobToolsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(NoobToolsWindow, self).__init__(parent, QtCore.Qt.Window | QtCore.Qt.Tool)

        self.setWindowTitle("NoobTools Suite v3.5 - Modern & Smooth UI")
        self.resize(480, 920)
        self.setMinimumSize(480, 820)
        self.setStyleSheet(MODERN_THEME_STYLESHEET) 

        self.threadpool = QtCore.QThreadPool()
        self.threadpool.setMaxThreadCount(min(max(os.cpu_count() or 4, 4), 8))
        self.current_worker = None
        self.scanner_worker = None
        
        self.favorites = []
        self.import_history = []
        self.relink_path = ""
        self.missing_assets = []
        self.root_path = ""
        self.user_dir = os.path.expanduser("~")
        self.config_file = os.path.join(self.user_dir, "NoobTools_Config.ini")
        self.cache_dir = os.path.join(tempfile.gettempdir(), "NoobTools_Cache")
        self.settings = {'enable_autobackup': True}
        self.settings_file = os.path.join(self.user_dir, "NoobTools_Settings.json")

        if not os.path.exists(self.cache_dir):
            try: os.makedirs(self.cache_dir)
            except Exception: pass

        self.setup_ui()
        self.setup_shortcuts()
        self.load_config()
        self.load_settings()
        self.load_import_history()
        self.auto_detect_project_path()

    def setup_ui(self):
        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setSpacing(10)
        layout_principal.setContentsMargins(12, 12, 12, 12)
        self.setLayout(layout_principal)

        title_label = QtWidgets.QLabel("NOOBTOOLS SUITE v3.5")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #007acc;")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        layout_principal.addWidget(title_label)

        self.tabs = QtWidgets.QTabWidget()
        layout_principal.addWidget(self.tabs)

        self.tab_manager = QtWidgets.QWidget()
        self.setup_asset_manager_tab()
        self.tabs.addTab(self.tab_manager, "Asset Manager")

        self.tab_fix = QtWidgets.QWidget()
        self.setup_noobfix_tab()
        self.tabs.addTab(self.tab_fix, "NoobFix")

        self.tab_history = QtWidgets.QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.tab_history, "History")

        self.tab_settings = QtWidgets.QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.tab_settings, "Settings")

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #777; font-size: 11px;")
        layout_principal.addWidget(self.status_label)

        # Aplicar cursor de mãozinha em todos os botões garantidamente (Backup ao QSS)
        for btn in self.findChildren(QtWidgets.QPushButton):
            btn.setCursor(QtCore.Qt.PointingHandCursor)

    # --- TAB: ASSET MANAGER ---
    def setup_asset_manager_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.tab_manager.setLayout(layout)

        # Library
        config_group = QtWidgets.QGroupBox("LIBRARY")
        config_layout = QtWidgets.QVBoxLayout()
        top_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_lib = QtWidgets.QPushButton("Select Library Folder...")
        self.btn_lib.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.btn_lib.customContextMenuRequested.connect(self.open_favorites_menu)
        self.btn_refresh = QtWidgets.QPushButton("R")
        self.btn_refresh.setFixedWidth(36)
        top_btn_layout.addWidget(self.btn_lib)
        top_btn_layout.addWidget(self.btn_refresh)
        self.lbl_path = QtWidgets.QLabel("No path selected")
        config_layout.addLayout(top_btn_layout)
        config_layout.addWidget(self.lbl_path)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Category & Subcategory
        cat_layout = QtWidgets.QHBoxLayout()
        cat_layout.addWidget(QtWidgets.QLabel("Category:"))
        self.combo_category = QtWidgets.QComboBox()
        self.combo_category.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        cat_layout.addWidget(self.combo_category)
        layout.addLayout(cat_layout)

        subcat_layout = QtWidgets.QHBoxLayout()
        subcat_layout.addWidget(QtWidgets.QLabel("Subfolder:"))
        self.combo_subcategory = QtWidgets.QComboBox()
        self.combo_subcategory.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.combo_subcategory.setVisible(False)
        subcat_layout.addWidget(self.combo_subcategory)
        layout.addLayout(subcat_layout)

        # Filters
        filter_group = QtWidgets.QGroupBox("FILTERS")
        layout_filtros = QtWidgets.QVBoxLayout()
        layout_botoes_filtro = QtWidgets.QHBoxLayout()
        self.btn_max = QtWidgets.QPushButton(".MAX"); self.btn_max.setCheckable(True)
        self.btn_fbx = QtWidgets.QPushButton(".FBX"); self.btn_fbx.setCheckable(True)
        self.btn_skp = QtWidgets.QPushButton(".SKP"); self.btn_skp.setCheckable(True)
        self.btn_obj = QtWidgets.QPushButton(".OBJ"); self.btn_obj.setCheckable(True)
        for b in [self.btn_max, self.btn_fbx, self.btn_skp, self.btn_obj]:
            b.clicked.connect(partial(self.toggle_filters, b))
            layout_botoes_filtro.addWidget(b)
        self.input_search = QtWidgets.QLineEdit()
        self.input_search.setPlaceholderText("Search...")
        self.input_search.setClearButtonEnabled(True)
        layout_filtros.addLayout(layout_botoes_filtro)
        layout_filtros.addWidget(self.input_search)
        filter_group.setLayout(layout_filtros)
        layout.addWidget(filter_group)

        # Asset List
        self.asset_list = DroppableAssetList()
        self.asset_list.setViewMode(QtWidgets.QListWidget.IconMode)
        self.asset_list.setIconSize(QtCore.QSize(170, 160))
        self.asset_list.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.asset_list.setSpacing(10)
        self.asset_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.asset_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.asset_list.customContextMenuRequested.connect(self.open_asset_context_menu)
        self.asset_list.files_dropped.connect(self.handle_dropped_files)
        layout.addWidget(self.asset_list)

        # Info
        info_group = QtWidgets.QGroupBox("ASSET INFO")
        layout_info = QtWidgets.QGridLayout()
        self.lbl_info_count = QtWidgets.QLabel("Items: 0")
        self.lbl_info_name = QtWidgets.QLabel("-")
        self.lbl_info_size = QtWidgets.QLabel("Size: -")
        self.lbl_info_date = QtWidgets.QLabel("Date: -")
        self.lbl_info_renderer = QtWidgets.QLabel("Renderer: -")
        self.lbl_info_renderer.setStyleSheet("color: #e67e22; font-weight: bold;")
        
        layout_info.addWidget(self.lbl_info_count, 0, 0, 1, 2)
        layout_info.addWidget(QtWidgets.QLabel("File:"), 1, 0); layout_info.addWidget(self.lbl_info_name, 1, 1)
        layout_info.addWidget(self.lbl_info_size, 2, 0); layout_info.addWidget(self.lbl_info_date, 2, 1)
        layout_info.addWidget(QtWidgets.QLabel("Render:"), 3, 0); layout_info.addWidget(self.lbl_info_renderer, 3, 1)
        info_group.setLayout(layout_info)
        layout.addWidget(info_group)

        # Tools
        grupo_ferramentas = QtWidgets.QGroupBox("TOOLS")
        layout_ferramentas = QtWidgets.QHBoxLayout()
        self.btn_open = QtWidgets.QPushButton("Open")
        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_group = QtWidgets.QPushButton("Group")
        self.btn_ungroup = QtWidgets.QPushButton("Ungroup")
        layout_ferramentas.addWidget(self.btn_open)
        layout_ferramentas.addWidget(self.btn_close)
        layout_ferramentas.addWidget(self.btn_group)
        layout_ferramentas.addWidget(self.btn_ungroup)
        grupo_ferramentas.setLayout(layout_ferramentas)
        layout.addWidget(grupo_ferramentas)

        # Progress & Import
        self.progress_bar = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_bar)
        
        layout_opcoes_import = QtWidgets.QHBoxLayout()
        self.chk_auto_layer = QtWidgets.QCheckBox("Auto Layer"); self.chk_auto_layer.setChecked(True)
        self.chk_prefix = QtWidgets.QCheckBox("Prefix")
        self.txt_prefix = QtWidgets.QLineEdit()
        self.txt_prefix.setEnabled(False)
        self.chk_prefix.toggled.connect(self.txt_prefix.setEnabled)
        layout_opcoes_import.addWidget(self.chk_auto_layer); layout_opcoes_import.addWidget(self.chk_prefix); layout_opcoes_import.addWidget(self.txt_prefix)
        layout.addLayout(layout_opcoes_import)

        # Botão Importar Massivo
        self.btn_import = QtWidgets.QPushButton("IMPORT TO SCENE")
        self.btn_import.setEnabled(False)
        self.btn_import.setObjectName("btnImport")
        self.btn_import.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(self.btn_import)

        # Connections
        self.btn_lib.clicked.connect(self.select_library_folder)
        self.btn_refresh.clicked.connect(self.refresh_ui)
        self.combo_category.currentIndexChanged.connect(self.on_category_changed)
        self.combo_subcategory.currentIndexChanged.connect(self.on_subcategory_changed)
        self.input_search.textChanged.connect(self.filter_assets)
        self.asset_list.itemDoubleClicked.connect(self.run_import_logic)
        self.asset_list.itemClicked.connect(self.update_asset_info)
        self.asset_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        self.btn_open.clicked.connect(lambda: pymxs.runtime.execute("max group open"))
        self.btn_close.clicked.connect(lambda: pymxs.runtime.execute("max group close"))
        self.btn_group.clicked.connect(lambda: pymxs.runtime.execute("max group group"))
        self.btn_ungroup.clicked.connect(lambda: pymxs.runtime.execute("max group ungroup"))
        self.btn_import.clicked.connect(self.run_import_logic)

    # --- TAB: NOOBFIX ---
    def setup_noobfix_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.tab_fix.setLayout(layout)

        lib_group = QtWidgets.QGroupBox("1. BIBLIOTECA")
        layout_biblio = QtWidgets.QVBoxLayout()
        layout_caminho = QtWidgets.QHBoxLayout()
        self.edt_relink_path = QtWidgets.QLineEdit()
        self.edt_relink_path.setReadOnly(True)
        self.btn_browse_relink = QtWidgets.QPushButton("...")
        self.btn_browse_relink.setFixedWidth(40)
        layout_caminho.addWidget(self.edt_relink_path); layout_caminho.addWidget(self.btn_browse_relink)
        self.lbl_relink_status = QtWidgets.QLabel("Selecione a pasta raiz")
        layout_biblio.addLayout(layout_caminho); layout_biblio.addWidget(self.lbl_relink_status)
        lib_group.setLayout(layout_biblio)
        layout.addWidget(lib_group)

        fav_group = QtWidgets.QGroupBox("2. FAVORITOS")
        layout_fav = QtWidgets.QHBoxLayout()
        self.lbx_favorites_fix = QtWidgets.QListWidget()
        self.lbx_favorites_fix.setMaximumHeight(80)
        layout_fav_botoes = QtWidgets.QVBoxLayout()
        self.btn_add_fav_fix = QtWidgets.QPushButton("+"); self.btn_add_fav_fix.setFixedWidth(30)
        self.btn_del_fav_fix = QtWidgets.QPushButton("-"); self.btn_del_fav_fix.setFixedWidth(30)
        layout_fav_botoes.addWidget(self.btn_add_fav_fix); layout_fav_botoes.addWidget(self.btn_del_fav_fix); layout_fav_botoes.addStretch()
        layout_fav.addWidget(self.lbx_favorites_fix); layout_fav.addLayout(layout_fav_botoes)
        fav_group.setLayout(layout_fav)
        layout.addWidget(fav_group)

        diag_group = QtWidgets.QGroupBox("3. DIAGNOSTICO")
        layout_diag = QtWidgets.QVBoxLayout()
        self.btn_scan_missing = QtWidgets.QPushButton("SCAN SCENE")
        self.btn_scan_missing.setObjectName("btnScan")
        self.lbx_missing = QtWidgets.QListWidget()
        self.lbx_missing.setMinimumHeight(150)
        self.lbl_help = QtWidgets.QLabel("(Duplo clique para selecionar objetos)")
        self.lbl_help.setObjectName("lblHelp")
        self.edt_selected_missing = QtWidgets.QLineEdit(); self.edt_selected_missing.setReadOnly(True)
        
        layout_diag_tools = QtWidgets.QHBoxLayout()
        self.btn_strip = QtWidgets.QPushButton("STRIP (Remover)")
        self.btn_strip.setObjectName("btnStrip"); self.btn_strip.setEnabled(False)
        self.btn_unc = QtWidgets.QPushButton("UNC (Rede)")
        self.btn_unc.setObjectName("btnUNC")
        layout_diag_tools.addWidget(self.btn_strip); layout_diag_tools.addWidget(self.btn_unc)
        
        layout_diag.addWidget(self.btn_scan_missing)
        layout_diag.addWidget(self.lbx_missing)
        layout_diag.addWidget(self.lbl_help)
        layout_diag.addWidget(self.edt_selected_missing)
        layout_diag.addLayout(layout_diag_tools)
        diag_group.setLayout(layout_diag)
        layout.addWidget(diag_group)

        exec_group = QtWidgets.QGroupBox("4. EXECUTAR")
        layout_exec = QtWidgets.QVBoxLayout()
        layout_exec_opcoes = QtWidgets.QHBoxLayout()
        self.chk_ignore_ext = QtWidgets.QCheckBox("Ignorar Extensao"); self.chk_ignore_ext.setChecked(True)
        self.chk_subfolders = QtWidgets.QCheckBox("Incluir Subpastas"); self.chk_subfolders.setChecked(True)
        layout_exec_opcoes.addWidget(self.chk_ignore_ext); layout_exec_opcoes.addWidget(self.chk_subfolders)
        
        self.lbl_info_files = QtWidgets.QLabel("Aguardando...")
        self.pb_relink = QtWidgets.QProgressBar()
        self.pb_relink.setObjectName("pbRelink")
        
        self.btn_run_relink = QtWidgets.QPushButton("BUSCAR E RELINKAR")
        self.btn_run_relink.setObjectName("btnRelink"); self.btn_run_relink.setEnabled(False)
        self.btn_collect = QtWidgets.QPushButton("COLETAR (Copy to Project)")
        
        layout_exec.addLayout(layout_exec_opcoes); layout_exec.addWidget(self.lbl_info_files); layout_exec.addWidget(self.pb_relink)
        layout_exec.addWidget(self.btn_run_relink); layout_exec.addWidget(self.btn_collect)
        exec_group.setLayout(layout_exec)
        layout.addWidget(exec_group)
        layout.addStretch()

        self.btn_browse_relink.clicked.connect(self.browse_relink_path)
        self.lbx_favorites_fix.itemClicked.connect(self.load_favorite_fix)
        self.btn_add_fav_fix.clicked.connect(self.add_favorite_fix)
        self.btn_del_fav_fix.clicked.connect(self.del_favorite_fix)
        self.btn_scan_missing.clicked.connect(self.scan_missing_files)
        self.lbx_missing.itemClicked.connect(self.on_missing_selected)
        self.lbx_missing.itemDoubleClicked.connect(self.select_objects_from_missing)
        self.btn_strip.clicked.connect(self.strip_missing_paths)
        self.btn_unc.clicked.connect(self.convert_to_unc)
        self.btn_run_relink.clicked.connect(self.start_relink_scanner) 
        self.btn_collect.clicked.connect(self.collect_files)

    # --- TAB: HISTORY ---
    def setup_history_tab(self):
        layout_history = QtWidgets.QVBoxLayout()
        self.tab_history.setLayout(layout_history)
        self.tbl_history = QtWidgets.QTableWidget()
        self.tbl_history.setColumnCount(4)
        self.tbl_history.setHorizontalHeaderLabels(["Date", "Time", "File", "Type"])
        self.tbl_history.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout_history.addWidget(self.tbl_history)
        layout_history_botoes = QtWidgets.QHBoxLayout()
        self.btn_clear_hist = QtWidgets.QPushButton("Clear"); self.btn_refresh_hist = QtWidgets.QPushButton("Refresh")
        layout_history_botoes.addWidget(self.btn_clear_hist); layout_history_botoes.addWidget(self.btn_refresh_hist); layout_history_botoes.addStretch()
        layout_history.addLayout(layout_history_botoes)
        self.btn_clear_hist.clicked.connect(self.clear_import_history)
        self.btn_refresh_hist.clicked.connect(self.refresh_history_table)

    # --- TAB: SETTINGS ---
    def setup_settings_tab(self):
        layout_settings = QtWidgets.QVBoxLayout()
        self.tab_settings.setLayout(layout_settings)
        
        grupo_backup = QtWidgets.QGroupBox("BACKUP")
        layout_backup = QtWidgets.QVBoxLayout()
        self.chk_autobackup = QtWidgets.QCheckBox("Auto-backup before operations")
        self.chk_autobackup.setChecked(True)
        layout_backup.addWidget(self.chk_autobackup)
        grupo_backup.setLayout(layout_backup)
        layout_settings.addWidget(grupo_backup)
        
        grupo_cache = QtWidgets.QGroupBox("CACHE")
        layout_cache = QtWidgets.QVBoxLayout()
        self.btn_clear_cache = QtWidgets.QPushButton("Clear Thumbnail Cache")
        self.lbl_cache_size = QtWidgets.QLabel("Calculating...")
        layout_cache.addWidget(self.btn_clear_cache); layout_cache.addWidget(self.lbl_cache_size)
        grupo_cache.setLayout(layout_cache)
        layout_settings.addWidget(grupo_cache)
        
        layout_settings.addStretch()
        
        self.btn_clear_cache.clicked.connect(self.manual_clear_cache)
        self.chk_autobackup.stateChanged.connect(self.on_autobackup_changed)
        self.update_cache_size_label()

    # ==========================================================================
    # LÓGICA
    # ==========================================================================
    def safe_path(self, path): return os.path.normpath(str(path)) if path else ""
    
    def select_library_folder(self):
        f = QtWidgets.QFileDialog.getExistingDirectory(self, "Library Root", self.root_path)
        if f:
            self.root_path = self.safe_path(f)
            self.lbl_path.setText(self.root_path)
            self.save_config(); self.refresh_ui()

    def refresh_ui(self):
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        if os.path.isdir(self.root_path):
            try:
                categories = [d for d in os.listdir(self.root_path) if os.path.isdir(os.path.join(self.root_path, d))]
                self.combo_category.addItems(sorted(categories))
            except Exception: pass
        self.combo_category.blockSignals(False)
        self.combo_subcategory.clear()
        self.combo_subcategory.setVisible(False)
        if self.combo_category.count() > 0: self.on_category_changed()
        else: self.asset_list.clear()

    def on_category_changed(self):
        category = self.combo_category.currentText()
        if not category or not self.root_path: return
        category_path = os.path.join(self.root_path, category)
        if not os.path.isdir(category_path): return

        subfolders = [f for f in os.listdir(category_path) if os.path.isdir(os.path.join(category_path, f))]
        has_direct_assets = False
        for sub in subfolders:
            sub_path = os.path.join(category_path, sub)
            if any(glob.glob(os.path.join(sub_path, ext)) for ext in ["*.max", "*.fbx", "*.obj", "*.3ds"]):
                has_direct_assets = True; break

        if has_direct_assets:
            self.combo_subcategory.setVisible(False)
            self.populate_asset_grid(category_path)
        else:
            self.combo_subcategory.blockSignals(True)
            self.combo_subcategory.clear()
            self.combo_subcategory.addItems(sorted(subfolders))
            self.combo_subcategory.setVisible(True)
            self.combo_subcategory.blockSignals(False)
            if subfolders: self.on_subcategory_changed()
            else: self.asset_list.clear()

    def on_subcategory_changed(self):
        category = self.combo_category.currentText()
        sub = self.combo_subcategory.currentText()
        if not category or not sub or not self.root_path: return
        asset_path = os.path.join(self.root_path, category, sub)
        self.populate_asset_grid(asset_path)

    def populate_asset_grid(self, folder_path):
        self.asset_list.clear()
        if self.current_worker:
            self.current_worker.stop()
            self.threadpool.waitForDone(500)
            self.current_worker = None

        if not os.path.isdir(folder_path): return

        asset_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        self.lbl_info_count.setText("Items: {}".format(len(asset_folders)))

        assets_to_load = []
        for name in asset_folders:
            path = os.path.join(folder_path, name)
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.UserRole, path)
            pix = QtGui.QPixmap(170, 160); pix.fill(QtGui.QColor(36, 36, 38))
            painter = QtGui.QPainter(pix); painter.setPen(QtGui.QColor(100,100,100))
            painter.drawText(pix.rect(), QtCore.Qt.AlignCenter, "Loading...")
            painter.end()
            item.setIcon(QtGui.QIcon(pix))
            self.asset_list.addItem(item)
            assets_to_load.append({'path': path, 'name': name})

        if assets_to_load:
            worker = ThumbnailLoader(assets_to_load, self.cache_dir)
            worker.signals.result_ready.connect(self.update_thumbnail)
            worker.signals.progress.connect(self.update_thumbnail_progress)
            self.current_worker = worker
            self.threadpool.start(worker)

    def update_thumbnail(self, path, icon):
        for i in range(self.asset_list.count()):
            it = self.asset_list.item(i)
            if it.data(QtCore.Qt.UserRole) == path:
                it.setIcon(icon); break

    def update_thumbnail_progress(self, progress, message):
        self.status_label.setText(message)
        if progress >= 100: QtCore.QTimer.singleShot(2000, lambda: self.status_label.setText("Ready"))

    def handle_dropped_files(self, files):
        for f in files:
            if os.path.isfile(f): self.import_single_asset(os.path.dirname(f))

    def find_main_file(self, folder):
        for ext in ["*.max", "*.fbx", "*.obj", "*.3ds"]:
            found = glob.glob(os.path.join(folder, ext))
            if found:
                found.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                return found[0]
        return None

    def run_import_logic(self):
        items = self.asset_list.selectedItems()
        if not items: return
        self.progress_bar.setValue(0)
        
        if len(items) > 1:
            if QtWidgets.QMessageBox.question(self, "Batch", "Import {} assets?".format(len(items)), QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                total = len(items)
                for idx, it in enumerate(items):
                    self.import_single_asset(it.data(QtCore.Qt.UserRole), silent=True)
                    val = int(float(idx + 1) / total * 100)
                    self.progress_bar.setValue(val)
                    QtWidgets.QApplication.processEvents()
                QtCore.QTimer.singleShot(1500, lambda: self.progress_bar.setValue(0))
        else:
            self.import_single_asset(items[0].data(QtCore.Qt.UserRole), silent=False)

    def import_single_asset(self, folder, silent=False):
        main_file = self.find_main_file(folder)
        if not main_file:
            if not silent: QtWidgets.QMessageBox.warning(self, "Warning", "No 3D file found in this asset folder.")
            return

        if not silent: 
            self.progress_bar.setValue(30)
            QtWidgets.QApplication.processEvents()

        if self.settings.get('enable_autobackup', True): self.create_backup()

        setup_bitmap_paths_for_asset(folder)
        rt = pymxs.runtime
        rt.clearSelection()
        
        try:
            ext = main_file.lower()
            if ext.endswith(".max"):
                try:
                    merge_dups = rt.Name("mergeDups")
                    use_scene_mtl = rt.Name("useSceneMtlDups")
                    select_opt = rt.Name("select")
                    rt.mergeMAXFile(main_file, merge_dups, use_scene_mtl, select_opt)
                except AttributeError:
                    rt.mergeMAXFile(main_file)
            elif ext.endswith((".fbx", ".obj", ".3ds")):
                rt.importFile(main_file)

            refresh_asset_tracker()

            if self.chk_auto_layer.isChecked():
                lname = "".join(c for c in os.path.basename(folder) if c.isalnum() or c in ('_','-'))
                rt.global_addSelectionToLayer(lname)
            
            if self.chk_prefix.isChecked() and self.txt_prefix.text():
                rt.global_renameSelection(self.txt_prefix.text(), "")
            
            self.import_history.insert(0, {'date': datetime.now().strftime('%Y-%m-%d'), 'time': datetime.now().strftime('%H:%M'), 'filename': os.path.basename(main_file), 'type': 'Geo'})
            self.refresh_history_table()
            self.save_import_history()
            
            if not silent: 
                self.progress_bar.setValue(100)
                QtCore.QTimer.singleShot(1500, lambda: self.progress_bar.setValue(0))
        except Exception as e:
            if not silent: self.progress_bar.setValue(0)
            QtWidgets.QMessageBox.critical(self, "Import Error", str(e))

    def auto_detect_project_path(self):
        try:
            mp = pymxs.runtime.maxfilepath
            if mp:
                self.relink_path = self.safe_path(mp)
                self.edt_relink_path.setText(self.relink_path)
                self.lbl_relink_status.setText("Auto-detected: Project Folder")
                self.btn_run_relink.setEnabled(True)
        except Exception: pass

    def browse_relink_path(self):
        f = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Library", self.relink_path)
        if f:
            self.relink_path = self.safe_path(f)
            self.edt_relink_path.setText(self.relink_path)
            self.btn_run_relink.setEnabled(True)

    def scan_missing_files(self):
        self.lbx_missing.clear()
        self.missing_assets = []
        try:
            rt = pymxs.runtime
            self.missing_assets = list(rt.global_getMissingAssets())
            self.missing_assets = sorted(list(set(self.missing_assets)))

            if not self.missing_assets:
                self.lbx_missing.addItem("-- CENA LIMPA --")
                self.edt_selected_missing.setText("")
                self.btn_strip.setEnabled(False)
                self.lbl_info_files.setText("Cena limpa!")
            else:
                for asset in self.missing_assets: self.lbx_missing.addItem(asset)
                self.btn_strip.setEnabled(True)
                self.edt_selected_missing.setText("Faltando: {} arquivos".format(len(self.missing_assets)))
        except Exception: pass

    def on_missing_selected(self, item): self.edt_selected_missing.setText(item.text())

    def select_objects_from_missing(self, item):
        path = item.text()
        if path == "-- CENA LIMPA --": return
        try:
            count = pymxs.runtime.global_selectObjectsFromMissing(path)
            if count > 0: self.lbl_info_files.setText("Selecionados: {} objetos".format(count))
            else: QtWidgets.QMessageBox.information(self, "Info", "Mapa não aplicado a objetos 3D diretos.")
        except Exception: pass

    def strip_missing_paths(self):
        if not self.missing_assets: return
        self.create_backup()
        if QtWidgets.QMessageBox.question(self, "Confirmar", "Remover caminhos quebrados? (Irreversível)", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            try:
                count = pymxs.runtime.global_stripMissingPaths(self.missing_assets)
                self.scan_missing_files()
                QtWidgets.QMessageBox.information(self, "Sucesso", "Removidos: {}".format(count))
            except Exception: pass

    def convert_to_unc(self):
        self.create_backup()
        if QtWidgets.QMessageBox.question(self, "UNC", "Converter caminhos locais para Rede (UNC)?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            try:
                count = pymxs.runtime.global_convertToUNC()
                self.scan_missing_files()
                QtWidgets.QMessageBox.information(self, "Sucesso", "Convertidos: {}".format(count))
            except Exception: pass

    def collect_files(self):
        self.create_backup()
        try:
            mp = pymxs.runtime.maxfilepath
            if not mp:
                QtWidgets.QMessageBox.warning(self, "Erro", "Salve a cena primeiro!")
                return
            save_dir = os.path.join(mp, "Maps")
            if QtWidgets.QMessageBox.question(self, "Coletar", "Copiar texturas para:\n{}\nContinuar?".format(save_dir), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.No: return
            
            count = pymxs.runtime.global_collectFiles(save_dir)
            QtWidgets.QMessageBox.information(self, "Sucesso", "Coletados {} arquivos.".format(count))
            self.scan_missing_files()
        except Exception: pass

    def start_relink_scanner(self):
        if not self.relink_path or not os.path.isdir(self.relink_path): return
        if not self.missing_assets:
            QtWidgets.QMessageBox.information(self, "Info", "Nada faltando!")
            return

        self.create_backup()
        self.pb_relink.setValue(0)
        self.lbl_info_files.setText("Lendo disco... (Processo em background)")
        self.btn_run_relink.setEnabled(False) 

        if self.scanner_worker:
            self.scanner_worker.stop()
            self.threadpool.waitForDone(500)

        self.scanner_worker = RelinkScannerWorker(self.relink_path, self.chk_subfolders.isChecked())
        self.scanner_worker.signals.scan_result.connect(self.process_relink_results)
        self.threadpool.start(self.scanner_worker)

    def process_relink_results(self, file_dict):
        self.pb_relink.setValue(50)
        
        if not file_dict:
            QtWidgets.QMessageBox.warning(self, "Erro", "Nenhum arquivo encontrado na pasta!")
            self.btn_run_relink.setEnabled(True)
            self.lbl_info_files.setText("Aguardando...")
            self.pb_relink.setValue(0)
            return

        self.lbl_info_files.setText("Relinkando...")
        rt = pymxs.runtime
        relink_count = 0
        has_atsobs = False
        try:
            rt.ATSOps.Visible = False
            rt.ATSOps.ClearSelection()
            has_atsobs = True
        except Exception: pass

        if not has_atsobs:
            QtWidgets.QMessageBox.warning(self, "Erro", "ATSOps não disponível nesta versão.")
            self.pb_relink.setValue(0); self.btn_run_relink.setEnabled(True)
            return

        total = len(self.missing_assets)
        for i, missing_path in enumerate(self.missing_assets):
            try:
                missing_name = os.path.basename(missing_path)
                search_key = os.path.splitext(missing_name.lower())[0]
                
                if search_key in file_dict:
                    candidates = file_dict[search_key]
                    best_match = None
                    
                    for cand in candidates:
                        if not self.chk_ignore_ext.isChecked():
                            if os.path.splitext(missing_path)[1].lower() == os.path.splitext(cand)[1].lower():
                                best_match = cand; break
                        else:
                            best_match = cand; break

                    if best_match:
                        rt.ATSOps.ClearSelection()
                        rt.ATSOps.SelectFiles([missing_path])
                        rt.ATSOps.RetargetSelection(best_match)
                        relink_count += 1
            except Exception: pass
            
            self.pb_relink.setValue(50 + int((float(i+1)/total)*50))
            QtWidgets.QApplication.processEvents()

        try: rt.ATSOps.Refresh()
        except Exception: pass
        
        self.scan_missing_files()
        self.pb_relink.setValue(100)
        self.lbl_info_files.setText("Recuperados: {}".format(relink_count))
        self.btn_run_relink.setEnabled(True)
        QtWidgets.QMessageBox.information(self, "Resultado", "Relinkados: {}".format(relink_count))

    def create_backup(self):
        if not self.settings.get('enable_autobackup', True): return
        try:
            mf = pymxs.runtime.maxfilepath
            if mf:
                bd = os.path.join(os.path.dirname(mf), "_backup")
                if not os.path.exists(bd): os.makedirs(bd)
                bf = os.path.join(bd, "{}_{}.max".format(os.path.splitext(os.path.basename(mf))[0], datetime.now().strftime("%H%M%S")))
                pymxs.runtime.saveMaxFile(bf, quiet=True)
        except Exception: pass

    def on_selection_changed(self): self.btn_import.setEnabled(len(self.asset_list.selectedItems()) > 0)

    def update_asset_info(self, item):
        f = self.find_main_file(item.data(QtCore.Qt.UserRole))
        if f:
            st = os.stat(f)
            self.lbl_info_name.setText(os.path.basename(f))
            self.lbl_info_size.setText("{:.1f} MB".format(st.st_size/(1024*1024)))
            self.lbl_info_date.setText(datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d'))
            try:
                render_guess = pymxs.runtime.global_guessRenderer(f)
                self.lbl_info_renderer.setText(str(render_guess))
            except Exception: self.lbl_info_renderer.setText("Unknown")
        else: 
            self.lbl_info_name.setText("No 3D file")
            self.lbl_info_size.setText("-"); self.lbl_info_date.setText("-"); self.lbl_info_renderer.setText("-")

    def toggle_filters(self, btn):
        for b in [self.btn_max, self.btn_fbx, self.btn_skp, self.btn_obj]:
            if b != btn: b.setChecked(False)
        self.filter_assets(self.input_search.text())

    def filter_assets(self, txt):
        mode = "ALL"
        if self.btn_max.isChecked(): mode = ".max"
        elif self.btn_fbx.isChecked(): mode = ".fbx"
        
        vc = 0
        for i in range(self.asset_list.count()):
            it = self.asset_list.item(i)
            name = os.path.basename(it.data(QtCore.Qt.UserRole)).lower()
            match = txt.lower() in name
            if mode != "ALL":
                match = match and len(glob.glob(os.path.join(it.data(QtCore.Qt.UserRole), "*"+mode))) > 0
            it.setHidden(not match)
            if match: vc += 1
        self.lbl_info_count.setText("Items: {}".format(vc))

    def open_asset_context_menu(self, pos):
        m = QtWidgets.QMenu(self)
        m.addAction("Import").triggered.connect(self.run_import_logic)
        def explore_folder(path):
            if sys.platform == 'win32': os.startfile(path)
            elif sys.platform == 'darwin':
                import subprocess
                subprocess.Popen(['open', path])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', path])
        item_path = self.asset_list.itemAt(pos).data(QtCore.Qt.UserRole)
        m.addAction("Explore").triggered.connect(lambda: explore_folder(item_path))
        qt_exec(m, self.asset_list.mapToGlobal(pos))
    
    def open_favorites_menu(self, pos):
        m = QtWidgets.QMenu(self)
        m.addAction("Add Current").triggered.connect(lambda: (self.favorites.append(self.root_path), self.save_config()))
        for fav in self.favorites:
            fav_path = fav
            m.addAction(os.path.basename(fav)).triggered.connect(partial(lambda f: (setattr(self, 'root_path', f), self.lbl_path.setText(f), self.refresh_ui()), fav_path))
        qt_exec(m, self.btn_lib.mapToGlobal(pos))

    def load_favorite_fix(self, item):
        if os.path.isdir(item.text()):
            self.relink_path = item.text(); self.edt_relink_path.setText(self.relink_path); self.btn_run_relink.setEnabled(True)
    def add_favorite_fix(self):
        if self.relink_path and self.relink_path not in [self.lbx_favorites_fix.item(i).text() for i in range(self.lbx_favorites_fix.count())]:
            self.lbx_favorites_fix.addItem(self.relink_path); self.save_config()
    def del_favorite_fix(self):
        self.lbx_favorites_fix.takeItem(self.lbx_favorites_fix.currentRow()); self.save_config()

    def load_config(self):
        s = QtCore.QSettings(self.config_file, QtCore.QSettings.IniFormat)
        self.root_path = s.value("LibPath", "")
        favs_raw = s.value("Favs")
        if favs_raw is None or favs_raw == "": self.favorites = []
        elif isinstance(favs_raw, str): self.favorites = [favs_raw] if favs_raw else []
        elif isinstance(favs_raw, list): self.favorites = [f for f in favs_raw if f]
        else: self.favorites = []
        favsfix_raw = s.value("FavsFix")
        if favsfix_raw is None or favsfix_raw == "": favsfix_list = []
        elif isinstance(favsfix_raw, str): favsfix_list = [favsfix_raw] if favsfix_raw else []
        elif isinstance(favsfix_raw, list): favsfix_list = [f for f in favsfix_raw if f]
        else: favsfix_list = []
        self.lbx_favorites_fix.addItems(favsfix_list)
        if self.root_path: self.lbl_path.setText(self.root_path); self.refresh_ui()

    def save_config(self):
        s = QtCore.QSettings(self.config_file, QtCore.QSettings.IniFormat)
        s.setValue("LibPath", self.root_path); s.setValue("Favs", self.favorites)
        s.setValue("FavsFix", [self.lbx_favorites_fix.item(i).text() for i in range(self.lbx_favorites_fix.count())])

    def setup_shortcuts(self):
        QtWidgets.QShortcut(QtGui.QKeySequence("F5"), self, self.refresh_ui)
        QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, self.close)

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f: self.settings = json.load(f)
                self.chk_autobackup.setChecked(self.settings.get('enable_autobackup', True))
        except Exception: self.settings = {'enable_autobackup': True}

    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f: json.dump(self.settings, f, indent=2)
        except Exception: pass

    def manual_clear_cache(self):
        try:
            if os.path.exists(self.cache_dir):
                for f in os.listdir(self.cache_dir):
                    try: os.remove(os.path.join(self.cache_dir, f))
                    except Exception: pass
            self.update_cache_size_label()
            QtWidgets.QMessageBox.information(self, "Success", "Cache cleared!")
        except Exception: pass

    def on_autobackup_changed(self):
        self.settings['enable_autobackup'] = self.chk_autobackup.isChecked(); self.save_settings()

    def update_cache_size_label(self):
        try:
            if os.path.exists(self.cache_dir):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(self.cache_dir):
                    for f in filenames:
                        try: total_size += os.path.getsize(os.path.join(dirpath, f))
                        except Exception: pass
                self.lbl_cache_size.setText("Cache Size: {:.2f} MB".format(total_size / (1024 * 1024)))
            else: self.lbl_cache_size.setText("Cache Size: 0 MB")
        except Exception: self.lbl_cache_size.setText("Cache Size: Error")

    def refresh_history_table(self):
        self.tbl_history.setRowCount(0)
        for e in self.import_history:
            r = self.tbl_history.rowCount(); self.tbl_history.insertRow(r)
            self.tbl_history.setItem(r, 0, QtWidgets.QTableWidgetItem(e['date']))
            self.tbl_history.setItem(r, 1, QtWidgets.QTableWidgetItem(e['time']))
            self.tbl_history.setItem(r, 2, QtWidgets.QTableWidgetItem(e['filename']))
            self.tbl_history.setItem(r, 3, QtWidgets.QTableWidgetItem(e.get('type', '')))

    def clear_import_history(self):
        self.import_history = []
        self.refresh_history_table(); self.save_import_history()

    def load_import_history(self):
        try:
            history_file = os.path.join(self.user_dir, "NoobTools_History.json")
            if os.path.exists(history_file):
                with open(history_file, 'r') as f: self.import_history = json.load(f)
                self.refresh_history_table()
        except Exception: self.import_history = []

    def save_import_history(self):
        try:
            history_file = os.path.join(self.user_dir, "NoobTools_History.json")
            with open(history_file, 'w') as f: json.dump(self.import_history, f, indent=2)
        except Exception: pass

    def closeEvent(self, e):
        self.save_config(); self.save_settings(); self.save_import_history()
        if self.current_worker: self.current_worker.stop()
        if self.scanner_worker: self.scanner_worker.stop()
        e.accept()

# ==============================================================================
# MAIN 
# ==============================================================================
_noob_tools_instance = None

def main():
    global _noob_tools_instance
    try:
        if _noob_tools_instance is not None:
            _noob_tools_instance.close()
            _noob_tools_instance.deleteLater()
    except Exception: pass
    
    mw = get_max_main_window()
    _noob_tools_instance = NoobToolsWindow(parent=mw)
    _noob_tools_instance.show()

if __name__ == "__main__":
    main()