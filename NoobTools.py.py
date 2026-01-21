import sys
import os
import glob
import logging
import tempfile
import time
from datetime import datetime

# ==============================================================================
# 0. COMPATIBILIDADE UNIVERSAL (MAX 2020-2024 vs MAX 2025+)
# ==============================================================================
try:
    # Tenta importar PySide6 (Max 2025/2026+)
    from PySide6 import QtWidgets, QtCore, QtGui
    IS_PYSIDE6 = True
except ImportError:
    try:
        # Se falhar, tenta PySide2 (Max 2020-2024)
        from PySide2 import QtWidgets, QtCore, QtGui
        IS_PYSIDE6 = False
    except ImportError:
        # Fallback extremo
        from PySide import QtWidgets, QtCore, QtGui
        IS_PYSIDE6 = False

# Helper para lidar com a mudança de nome de funcoes (exec_ vs exec)
def qt_exec(obj, *args):
    if hasattr(obj, 'exec'):
        return obj.exec(*args)
    elif hasattr(obj, 'exec_'):
        return obj.exec_(*args)
    return None

import pymxs

# ==============================================================================
# 1. LOGGING
# ==============================================================================
LOG_FILE = os.path.join(tempfile.gettempdir(), "NoobTools_Log.txt")
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, filemode='w', format='%(asctime)s - %(message)s')

def log_info(msg): logging.info(msg); print(f"[NoobTools] {msg}")
def log_error(msg): logging.error(msg); print(f"[NoobTools Error] {msg}")

# ==============================================================================
# 2. LÓGICA MAXSCRIPT
# ==============================================================================
MAXSCRIPT_LOGIC = """
global global_NoobTools_LastImported = undefined

fn global_forcePivotToBottom o =
(
    if isValidNode o do
    (
        local bb = nodeGetBoundingBox o (matrix3 1)
        local bmin = bb[1]; local bmax = bb[2]
        o.pivot = [(bmin.x + bmax.x) / 2.0, (bmin.y + bmax.y) / 2.0, bmin.z]
    )
)

fn global_relink_direct filenames_list fullpaths_list =
(
    local countFixed = 0
    local supportedAssets = #(
        #(BitmapTexture, "filename"), #(CoronaBitmap, "filename"),
        #(VRayBitmap, "HDRIMapName"), #(VRayHDRI, "HDRIMapName"),       
        #(CoronaLight, "iesFile"), #(VRayIES, "ies_file"),
        #(VRayProxy, "filename"), #(CoronaProxy, "filename"),
        #(AiImage, "filename")
    )

    for assetDef in supportedAssets do
    (
        local assetClass = assetDef[1]; local propName = assetDef[2]
        if (assetClass != undefined) do
        (
            for inst in (getClassInstances assetClass) do
            (
                if (isProperty inst propName) do
                (
                    local currentPath = getProperty inst propName
                    if (currentPath != undefined) and (currentPath != "") and (not doesFileExist currentPath) do
                    (
                        local fName = filenameFromPath currentPath
                        if fName != undefined do
                        (
                            local idx = findItem filenames_list (toLower fName)
                            if idx > 0 do
                            (
                                try ( setProperty inst propName fullpaths_list[idx]; countFixed += 1 ) catch()
                            )
                        )
                    )
                )
            )
        )
    )
    return countFixed
)
"""
try: pymxs.runtime.execute(MAXSCRIPT_LOGIC)
except Exception as e: log_error(str(e))

# ==============================================================================
# 3. THREADING
# ==============================================================================
class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal(); result_ready = QtCore.Signal(str, QtGui.QIcon)

class ThumbnailLoader(QtCore.QRunnable):
    def __init__(self, asset_data):
        super(ThumbnailLoader, self).__init__()
        self.asset_data = asset_data
        self.signals = WorkerSignals()
        self.is_running = True

    def run(self):
        for data in self.asset_data:
            if not self.is_running: break
            folder_path = data['path']; asset_name = data['name']; thumb_path = None
            try:
                parent_dir = os.path.dirname(folder_path)
                possible_exts = [".jpg", ".png", ".jpeg", ".bmp"]
                
                # 1. Busca na Raiz
                for ext in possible_exts:
                    attempt = os.path.join(parent_dir, asset_name + ext)
                    if os.path.exists(attempt): thumb_path = attempt; break
                # 2. Busca na Pasta
                if not thumb_path and os.path.isdir(folder_path):
                    with os.scandir(folder_path) as entries:
                        for entry in entries:
                            if entry.is_file() and entry.name.lower().endswith(tuple(possible_exts)):
                                thumb_path = entry.path; break
                
                final_w, final_h = 170, 160
                final_pix = QtGui.QPixmap(final_w, final_h)
                final_pix.fill(QtGui.QColor(35, 35, 38))
                
                if thumb_path:
                    pixmap = QtGui.QPixmap(thumb_path)
                    if not pixmap.isNull():
                        painter = QtGui.QPainter(final_pix)
                        scaled = pixmap.scaled(final_w, final_h-30, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                        x_pos = (final_w - scaled.width()) / 2
                        painter.drawPixmap(int(x_pos), 0, scaled)
                        painter.end()
                
                painter = QtGui.QPainter(final_pix)
                painter.setPen(QtGui.QColor(200, 200, 200))
                font = painter.font(); font.setPointSize(9); painter.setFont(font)
                painter.drawText(QtCore.QRect(0, final_h-30, final_w, 30), QtCore.Qt.AlignCenter, asset_name)
                painter.end()

                self.signals.result_ready.emit(folder_path, QtGui.QIcon(final_pix))
            except: continue
        self.signals.finished.emit()

    def stop(self): self.is_running = False

# ==============================================================================
# 4. ESTILO VISUAL
# ==============================================================================
DARK_THEME_STYLESHEET = """
QWidget { background-color: #1e1e1e; color: #e0e0e0; font-family: "Segoe UI", sans-serif; font-size: 11px; }

/* Group Box */
QGroupBox { border: 1px solid #333; border-radius: 4px; margin-top: 8px; padding-top: 15px; font-weight: bold; color: #777; background-color: #222222; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; left: 10px; background-color: #222222; }

/* Buttons */
QPushButton { background-color: #333337; border: 1px solid #2a2a2a; border-radius: 3px; color: #cccccc; padding: 6px; min-height: 22px; }
QPushButton:hover { background-color: #454549; color: #ffffff; border: 1px solid #555; }
QPushButton:pressed { background-color: #222; }
QPushButton:checked { background-color: #007acc; border: 1px solid #005f9e; color: white; font-weight: bold; }
QPushButton#btnImport { background-color: #007acc; color: white; font-weight: bold; font-size: 13px; padding: 12px; border-radius: 4px; border: none; }
QPushButton#btnImport:hover { background-color: #008be6; }

/* Inputs */
QLineEdit, QComboBox { background-color: #181818; border: 1px solid #3e3e42; border-radius: 3px; padding: 5px; color: white; }

/* List Widget */
QListWidget { background-color: #181818; border: 1px solid #333; border-radius: 4px; padding: 5px; outline: none; }
QListWidget::item { background-color: #252526; border-radius: 4px; }
QListWidget::item:selected { background-color: #333; border: 1px solid #007acc; }
QListWidget::item:hover { background-color: #2d2d30; border: 1px solid #444; }

/* Scrollbar (Sem Azul) */
QScrollBar:vertical { border: none; background: #181818; width: 14px; margin: 0px; }
QScrollBar::handle:vertical { background: #444; min-height: 20px; border-radius: 4px; margin: 2px; }
QScrollBar::handle:vertical:hover { background: #555; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; background: none; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: #181818; border: none; }

QScrollBar:horizontal { border: none; background: #181818; height: 14px; margin: 0px; }
QScrollBar::handle:horizontal { background: #444; min-width: 20px; border-radius: 4px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background: #555; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; background: none; border: none; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: #181818; border: none; }

/* Progress Bar */
QProgressBar { border: 1px solid #333; border-radius: 3px; background-color: #181818; text-align: center; color: white; font-weight: bold; }
QProgressBar::chunk { background-color: #007acc; width: 10px; margin: 0.5px; }

/* Status Labels */
QLabel#lblInfoTitle { color: #888; font-weight: bold; }
QLabel#lblInfoValue { color: #ddd; }
"""

def get_max_main_window():
    app = QtWidgets.QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QtWidgets.QMainWindow) and widget.parent() is None: return widget
    return app.activeWindow()

# ==============================================================================
# 5. JANELA PRINCIPAL
# ==============================================================================
class NoobToolsWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(NoobToolsWindow, self).__init__(parent)
        self.setWindowTitle("NoobTools Asset Manager")
        self.resize(440, 900)
        self.setFixedWidth(440)
        self.setWindowFlags(QtCore.Qt.Window) # Minimizar/Maximizar
        self.setStyleSheet(DARK_THEME_STYLESHEET)
        
        self.threadpool = QtCore.QThreadPool()
        self.current_worker = None
        self.favorites = []

        try:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            icon_path = os.path.join(script_dir, "noob_icon.png")
            if os.path.exists(icon_path): self.setWindowIcon(QtGui.QIcon(icon_path))
        except: pass
        
        self.root_path = ""; user_dir = os.path.expanduser("~")
        self.config_file = os.path.join(user_dir, "NoobTools_Config.ini")

        # Layout Main
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(10); main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(main_layout)

        # 1. Library
        config_group = QtWidgets.QGroupBox("LIBRARY")
        config_layout = QtWidgets.QVBoxLayout()
        top_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_lib = QtWidgets.QPushButton("Select Library Folder...")
        self.btn_lib.setToolTip("Right Click for Favorites")
        self.btn_lib.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.btn_lib.customContextMenuRequested.connect(self.open_favorites_menu)
        self.btn_refresh = QtWidgets.QPushButton("R"); self.btn_refresh.setFixedWidth(30)
        top_btn_layout.addWidget(self.btn_lib); top_btn_layout.addWidget(self.btn_refresh)
        self.lbl_path = QtWidgets.QLabel("No path selected")
        self.lbl_path.setStyleSheet("color: #555; font-family: Consolas; font-size: 10px;")
        config_layout.addLayout(top_btn_layout); config_layout.addWidget(self.lbl_path)
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # 2. Filters
        filter_group = QtWidgets.QGroupBox("FILTERS")
        filter_layout = QtWidgets.QVBoxLayout()
        type_layout = QtWidgets.QHBoxLayout()
        self.btn_max = QtWidgets.QPushButton(".MAX"); self.btn_max.setCheckable(True)
        self.btn_max.clicked.connect(lambda: self.toggle_filters(self.btn_max))
        self.btn_fbx = QtWidgets.QPushButton(".FBX"); self.btn_fbx.setCheckable(True)
        self.btn_fbx.clicked.connect(lambda: self.toggle_filters(self.btn_fbx))
        self.btn_skp = QtWidgets.QPushButton(".SKP"); self.btn_skp.setCheckable(True)
        self.btn_skp.clicked.connect(lambda: self.toggle_filters(self.btn_skp))
        type_layout.addWidget(self.btn_max); type_layout.addWidget(self.btn_fbx); type_layout.addWidget(self.btn_skp)
        self.combo_category = QtWidgets.QComboBox()
        self.input_search = QtWidgets.QLineEdit()
        self.input_search.setPlaceholderText("Search name...")
        filter_layout.addLayout(type_layout)
        filter_layout.addWidget(self.combo_category)
        filter_layout.addWidget(self.input_search)
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # 3. Grid
        self.asset_list = QtWidgets.QListWidget()
        self.asset_list.setViewMode(QtWidgets.QListWidget.IconMode)
        self.asset_list.setIconSize(QtCore.QSize(170, 160))
        self.asset_list.setResizeMode(QtWidgets.QListWidget.Adjust)
        self.asset_list.setSpacing(10)
        self.asset_list.setMovement(QtWidgets.QListWidget.Static)
        main_layout.addWidget(self.asset_list)

        # --- INFO AREA ---
        info_group = QtWidgets.QGroupBox("ASSET INFO")
        info_layout = QtWidgets.QVBoxLayout()
        stats_layout = QtWidgets.QGridLayout()
        stats_layout.setSpacing(5)
        
        self.lbl_info_count = QtWidgets.QLabel("Items: 0")
        self.lbl_info_count.setObjectName("lblInfoTitle")
        stats_layout.addWidget(self.lbl_info_count, 0, 0, 1, 2)

        self.lbl_info_name = QtWidgets.QLabel("-")
        self.lbl_info_name.setObjectName("lblInfoValue")
        self.lbl_info_size = QtWidgets.QLabel("Size: -")
        self.lbl_info_size.setObjectName("lblInfoTitle")
        self.lbl_info_date = QtWidgets.QLabel("Date: -")
        self.lbl_info_date.setObjectName("lblInfoTitle")

        stats_layout.addWidget(QtWidgets.QLabel("File:"), 1, 0); stats_layout.addWidget(self.lbl_info_name, 1, 1)
        stats_layout.addWidget(self.lbl_info_size, 2, 0)
        stats_layout.addWidget(self.lbl_info_date, 2, 1)
        
        info_layout.addLayout(stats_layout)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)

        # 4. Tools
        tools_layout = QtWidgets.QHBoxLayout()
        hierarchy_group = QtWidgets.QGroupBox("HIERARCHY")
        h_layout = QtWidgets.QGridLayout()
        self.btn_open = QtWidgets.QPushButton("Open"); self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_group = QtWidgets.QPushButton("Group"); self.btn_ungroup = QtWidgets.QPushButton("Ungroup")
        h_layout.addWidget(self.btn_open, 0, 0); h_layout.addWidget(self.btn_close, 0, 1)
        h_layout.addWidget(self.btn_group, 1, 0); h_layout.addWidget(self.btn_ungroup, 1, 1)
        hierarchy_group.setLayout(h_layout)
        pivot_group = QtWidgets.QGroupBox("PIVOT")
        p_layout = QtWidgets.QVBoxLayout(); p_layout.setContentsMargins(5, 15, 5, 5)
        self.btn_base_z = QtWidgets.QPushButton("BASE Z"); self.btn_base_z.setMinimumHeight(40)
        p_layout.addWidget(self.btn_base_z)
        pivot_group.setLayout(p_layout)
        tools_layout.addWidget(hierarchy_group, 2); tools_layout.addWidget(pivot_group, 1)
        main_layout.addLayout(tools_layout)

        # 5. Management
        manage_group = QtWidgets.QGroupBox("ASSET MANAGEMENT")
        m_layout = QtWidgets.QHBoxLayout()
        self.btn_reset_xform = QtWidgets.QPushButton("Reset XForm")
        self.btn_relink = QtWidgets.QPushButton("Relink Maps")
        m_layout.addWidget(self.btn_reset_xform); m_layout.addWidget(self.btn_relink)
        manage_group.setLayout(m_layout)
        main_layout.addWidget(manage_group)

        # Progress Bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ready")
        self.progress_bar.setStyleSheet("font-size: 10px; height: 12px;")
        main_layout.addWidget(self.progress_bar)

        # 6. Import
        self.btn_import = QtWidgets.QPushButton(">>> IMPORT TO SCENE <<<")
        self.btn_import.setObjectName("btnImport")
        main_layout.addWidget(self.btn_import)

        # Connections
        self.btn_lib.clicked.connect(self.select_library_folder)
        self.btn_refresh.clicked.connect(self.refresh_ui)
        self.combo_category.currentIndexChanged.connect(self.load_assets_from_combo)
        self.input_search.textChanged.connect(self.filter_assets)
        self.asset_list.itemDoubleClicked.connect(self.run_import_logic)
        self.asset_list.itemClicked.connect(self.update_asset_info)
        self.asset_list.currentItemChanged.connect(self.update_asset_info)

        self.btn_open.clicked.connect(lambda: self.safe_execute("max group open"))
        self.btn_close.clicked.connect(lambda: self.safe_execute("max group close"))
        self.btn_group.clicked.connect(lambda: self.safe_execute("max group group"))
        self.btn_ungroup.clicked.connect(lambda: self.safe_execute("max group ungroup"))
        self.btn_base_z.clicked.connect(self.run_pivot_base_z)
        self.btn_reset_xform.clicked.connect(self.run_reset_xform)
        self.btn_relink.clicked.connect(self.run_relink_only)
        self.btn_import.clicked.connect(self.run_import_logic)

        self.load_config()

    # --- INFO & STATS ---
    def update_asset_info(self):
        item = self.asset_list.currentItem()
        if not item:
            self.lbl_info_name.setText("-")
            self.lbl_info_size.setText("Size: -")
            self.lbl_info_date.setText("Date: -")
            return

        asset_path = item.data(QtCore.Qt.UserRole)
        target_file = None
        for ext in ["*.max", "*.fbx", "*.skp", "*.obj"]:
            found = glob.glob(os.path.join(asset_path, ext))
            if found: target_file = found[0]; break
        
        if target_file:
            try:
                stats = os.stat(target_file)
                size_mb = stats.st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d')
                self.lbl_info_name.setText(os.path.basename(target_file))
                size_str = f"{size_mb:.2f} MB"
                if size_mb > 100: self.lbl_info_size.setText(f"Size: <span style='color:#ff5555'>{size_str}</span>")
                else: self.lbl_info_size.setText(f"Size: {size_str}")
                self.lbl_info_date.setText(f"Date: {mod_time}")
            except: self.lbl_info_name.setText("Error reading file")
        else:
            self.lbl_info_name.setText("No 3D file found")
            self.lbl_info_size.setText("Size: -")

    # --- PROGRESS BAR HELPER ---
    def update_progress(self, val, message):
        self.progress_bar.setValue(val)
        self.progress_bar.setFormat(message)
        QtWidgets.QApplication.processEvents()

    # --- FILTROS ---
    def toggle_filters(self, clicked_btn):
        if clicked_btn.isChecked():
            if clicked_btn != self.btn_max: self.btn_max.setChecked(False)
            if clicked_btn != self.btn_fbx: self.btn_fbx.setChecked(False)
            if clicked_btn != self.btn_skp: self.btn_skp.setChecked(False)
        self.filter_assets(self.input_search.text())

    def filter_assets(self, text):
        search_text = text.lower()
        mode = "ALL"
        if self.btn_max.isChecked(): mode = ".max"
        elif self.btn_fbx.isChecked(): mode = ".fbx"
        elif self.btn_skp.isChecked(): mode = ".skp"

        visible_count = 0
        for i in range(self.asset_list.count()):
            item = self.asset_list.item(i)
            folder_path = item.data(QtCore.Qt.UserRole)
            asset_name = os.path.basename(folder_path).lower()
            match_name = search_text in asset_name
            match_type = True
            if mode != "ALL":
                has_file = len(glob.glob(os.path.join(folder_path, "*" + mode))) > 0
                if not has_file: match_type = False
            
            should_hide = not (match_name and match_type)
            item.setHidden(should_hide)
            if not should_hide: visible_count += 1
            
        self.lbl_info_count.setText(f"Items: {visible_count}")

    # --- FAVORITOS (UNIVERSAL MENU FIX) ---
    def open_favorites_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(DARK_THEME_STYLESHEET)
        menu.addAction("⭐ Add Current to Favorites").triggered.connect(self.add_favorite)
        menu.addSeparator()
        if not self.favorites: menu.addAction("No favorites saved").setEnabled(False)
        else:
            for fav in self.favorites:
                # Usar lambda seguro para PySide2/6
                menu.addAction(f"📂 {os.path.basename(fav)}").triggered.connect(lambda c=False, p=fav: self.load_favorite(p))
        menu.addSeparator(); menu.addAction("Clear Favorites").triggered.connect(self.clear_favorites)
        
        # Executa o menu com compatibilidade (exec_ vs exec)
        qt_exec(menu, self.btn_lib.mapToGlobal(pos))

    def add_favorite(self):
        if self.root_path and os.path.isdir(self.root_path) and self.root_path not in self.favorites:
            self.favorites.append(self.root_path); self.save_config()
    
    def load_favorite(self, path):
        if os.path.isdir(path): self.root_path = path; self.lbl_path.setText(self.root_path); self.save_config(); self.refresh_ui()

    def clear_favorites(self): self.favorites = []; self.save_config()

    # --- CORE ---
    def safe_execute(self, cmd):
        try: pymxs.runtime.execute(cmd)
        except Exception as e: log_error(f"Cmd Error: {e}")

    def select_library_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Library Root", self.root_path)
        if folder:
            self.root_path = folder.replace("/", "\\"); self.lbl_path.setText(self.root_path); self.save_config(); self.refresh_ui()

    def refresh_ui(self):
        self.combo_category.blockSignals(True); self.combo_category.clear()
        if os.path.isdir(self.root_path):
            try:
                dirs = [d for d in os.listdir(self.root_path) if os.path.isdir(os.path.join(self.root_path, d))]
                self.combo_category.addItems(sorted(dirs))
            except: pass
        self.combo_category.blockSignals(False); self.load_assets_from_combo()

    def load_assets_from_combo(self):
        cat_name = self.combo_category.currentText()
        if not cat_name: return
        self.populate_grid(os.path.join(self.root_path, cat_name))

    def populate_grid(self, folder_path):
        self.asset_list.clear()
        if self.current_worker: self.current_worker.stop()
        if not os.path.isdir(folder_path): return
        try: subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        except: return

        self.lbl_info_count.setText(f"Items: {len(subfolders)}")

        assets_to_load = []
        for asset_name in subfolders:
            asset_full_path = os.path.join(folder_path, asset_name)
            item = QtWidgets.QListWidgetItem(asset_name)
            item.setToolTip(asset_name)
            item.setData(QtCore.Qt.UserRole, asset_full_path)
            pixmap = QtGui.QPixmap(170, 160); pixmap.fill(QtGui.QColor(45, 45, 45))
            painter = QtGui.QPainter(pixmap); painter.setPen(QtGui.QColor(100, 100, 100))
            painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, "Loading..."); painter.end()
            item.setIcon(QtGui.QIcon(pixmap))
            self.asset_list.addItem(item)
            assets_to_load.append({'path': asset_full_path, 'name': asset_name})

        worker = ThumbnailLoader(assets_to_load)
        worker.signals.result_ready.connect(lambda p, i: [item.setIcon(i) for x in range(self.asset_list.count()) if (item := self.asset_list.item(x)).data(QtCore.Qt.UserRole) == p])
        self.current_worker = worker; self.threadpool.start(worker)

    # --- IMPORT & RELINK ---
    def run_import_logic(self):
        items = self.asset_list.selectedItems()
        if not items: return
        asset_path = items[0].data(QtCore.Qt.UserRole)
        file_to_import = None
        for ext in ["*.max", "*.fbx", "*.skp", "*.obj", "*.3ds"]:
            found = glob.glob(os.path.join(asset_path, ext))
            if found: file_to_import = found[0]; break
        
        if not file_to_import: QtWidgets.QMessageBox.warning(self, "Error", "No 3D file found."); return

        try:
            self.update_progress(10, "Starting Import...")
            rt = pymxs.runtime
            log_info(f"Importing: {file_to_import}")
            file_lower = file_to_import.lower()
            
            self.update_progress(30, f"Importing {os.path.splitext(os.path.basename(file_to_import))[1]}...")
            
            if file_lower.endswith(".max"):
                rt.mergeMAXFile(file_to_import, rt.Name("mergeDups"), rt.Name("useSceneMtlDups"), rt.Name("select"))
            elif file_lower.endswith(".fbx"):
                rt.importFile(file_to_import, rt.Name("noPrompt"))
            elif file_lower.endswith(".skp"):
                rt.importFile(file_to_import)
            else:
                rt.importFile(file_to_import)
            
            self.update_progress(60, "Relinking Textures...")
            self.run_relink_internal(asset_path, silent=True)
            
            self.update_progress(80, "Adjusting Pivots...")
            self.run_pivot_base_z()
            rt.redrawViews()
            
            self.update_progress(100, "Import Complete!")
            QtCore.QTimer.singleShot(2000, lambda: self.update_progress(0, "Ready"))
            
        except Exception as e:
            self.update_progress(0, "Error!")
            log_error(str(e))
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def run_relink_only(self):
        items = self.asset_list.selectedItems()
        if not items: QtWidgets.QMessageBox.information(self, "Info", "Select an asset to use as source."); return
        asset_path = items[0].data(QtCore.Qt.UserRole)
        self.update_progress(20, "Scanning Files...")
        self.run_relink_internal(asset_path, silent=False)
        self.update_progress(100, "Relink Done")
        QtCore.QTimer.singleShot(1500, lambda: self.update_progress(0, "Ready"))

    def run_relink_internal(self, asset_path, silent=False):
        try:
            search_folders = set()
            search_folders.add(asset_path)
            parent_dir = os.path.dirname(asset_path); search_folders.add(parent_dir)
            for name in ["maps", "Maps", "textures", "Textures", "images", "Images"]:
                candidate = os.path.join(parent_dir, name)
                if os.path.isdir(candidate): search_folders.add(candidate)
            
            if self.root_path and os.path.isdir(self.root_path):
                 search_folders.add(self.root_path)
                 for name in ["maps", "Maps", "textures", "Textures"]:
                     candidate = os.path.join(self.root_path, name)
                     if os.path.isdir(candidate): search_folders.add(candidate)

            files_names = []; files_fullpaths = []
            for folder in search_folders:
                for root, dirs, files in os.walk(folder):
                    for f in files:
                        files_names.append(f.lower()); files_fullpaths.append(os.path.join(root, f).replace("\\", "/"))
            
            if not files_names:
                if not silent: QtWidgets.QMessageBox.warning(self, "Relink", "No files found."); return

            count = pymxs.runtime.global_relink_direct(files_names, files_fullpaths)
            pymxs.runtime.ATSOps.Visible = False; pymxs.runtime.ATSOps.Refresh()
            
            if not silent:
                if count > 0: QtWidgets.QMessageBox.information(self, "Relink", f"Success! {count} assets relinked.")
                else: QtWidgets.QMessageBox.information(self, "Relink", "No missing files matched.")
        except Exception as e:
            log_error(str(e)); 
            if not silent: QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def run_pivot_base_z(self):
        try:
            rt = pymxs.runtime
            for obj in rt.selection: rt.global_forcePivotToBottom(obj)
            rt.redrawViews()
        except: pass

    def run_reset_xform(self):
        try:
            rt = pymxs.runtime
            for obj in rt.selection:
                if not rt.isGroupHead(obj): rt.resetXForm(obj); rt.collapseStack(obj)
            self.run_pivot_base_z()
        except: pass

    def load_config(self):
        settings = QtCore.QSettings(self.config_file, QtCore.QSettings.IniFormat)
        self.root_path = settings.value("LibraryPath", "")
        favs = settings.value("Favorites", [])
        self.favorites = favs if isinstance(favs, list) else [favs]
        if self.root_path and os.path.isdir(self.root_path):
            self.lbl_path.setText(self.root_path); self.refresh_ui()

    def save_config(self):
        settings = QtCore.QSettings(self.config_file, QtCore.QSettings.IniFormat)
        settings.setValue("LibraryPath", self.root_path)
        settings.setValue("Favorites", self.favorites)

    def closeEvent(self, event):
        if self.current_worker: self.current_worker.stop()
        self.threadpool.clear(); event.accept()

# --- EXEC ---
try: noob_tools_ui.close(); noob_tools_ui.deleteLater()
except: pass
max_win = get_max_main_window()
noob_tools_ui = NoobToolsWindow(parent=max_win)
noob_tools_ui.show()