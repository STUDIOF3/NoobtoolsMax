# -*- coding: utf-8 -*-
import os
import sys
import glob
import json
from datetime import datetime
from functools import partial
import tempfile
import pymxs

from src.utils.qt_compat import QtWidgets, QtCore, QtGui, qt_exec, IS_PYSIDE6
from src.utils.logger import log_error, log_info, log_warning
from src.core.threads import WorkerSignals, ThumbnailLoader, RelinkScannerWorker
from src.ui.widgets import DroppableAssetList
from src.ui.style import MODERN_THEME_STYLESHEET

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
        self.refresh_materials()
        self.auto_detect_project_path()

    def show_toast(self, message):
        """Exibe uma notificação flutuante com fallback para o Listener."""
        print("[NoobTools] " + message)
        try:
            from src.ui.widgets import ToastNotification
            ToastNotification(self, message)
        except Exception as e:
            print("[NoobTools Error] Falha ao exibir Toast: " + str(e))

    def setup_ui(self):
        layout_principal = QtWidgets.QVBoxLayout()
        layout_principal.setSpacing(10)
        layout_principal.setContentsMargins(12, 12, 12, 12)
        self.setLayout(layout_principal)

        title_label = QtWidgets.QLabel("NOOBTOOLS SUITE v4.0")
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

        self.tab_materials = QtWidgets.QWidget()
        self.setup_material_manager_tab()
        self.tabs.addTab(self.tab_materials, "Materials")

        self.tab_settings = QtWidgets.QWidget()
        self.setup_settings_tab()
        self.tabs.addTab(self.tab_settings, "Settings")

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("color: #777; font-size: 11px;")
        layout_principal.addWidget(self.status_label)

        # Aplicar cursor de mãozinha em todos os botões garantidamente
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

        # 5. TOOLS EXTRAS
        extra_group = QtWidgets.QGroupBox("5. TOOLS EXTRAS")
        layout_extra = QtWidgets.QHBoxLayout()
        self.btn_clean_scene = QtWidgets.QPushButton("CLEAN SCENE")
        self.btn_clean_scene.setToolTip("Remove camadas vazias e grupos vazios")
        self.btn_check_scale = QtWidgets.QPushButton("CHECK SCALE")
        self.btn_check_scale.setToolTip("Verifica as unidades do sistema")
        layout_extra.addWidget(self.btn_clean_scene)
        layout_extra.addWidget(self.btn_check_scale)
        extra_group.setLayout(layout_extra)
        layout.addWidget(extra_group)
        
        layout.addStretch()

        self.btn_clean_scene.clicked.connect(self.run_scene_cleaner)
        self.btn_check_scale.clicked.connect(self.run_scale_checker)

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

    # --- TAB: MATERIAL MANAGER ---
    def setup_material_manager_tab(self):
        layout = QtWidgets.QVBoxLayout()
        self.tab_materials.setLayout(layout)

        # 1. Lib & Categories
        lib_group = QtWidgets.QGroupBox("1. MATERIAL LIBRARY")
        lib_layout = QtWidgets.QVBoxLayout()
        
        cat_layout = QtWidgets.QHBoxLayout()
        cat_layout.addWidget(QtWidgets.QLabel("Category:"))
        self.combo_category_mat = QtWidgets.QComboBox()
        self.combo_category_mat.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        cat_layout.addWidget(self.combo_category_mat)
        
        subcat_layout = QtWidgets.QHBoxLayout()
        subcat_layout.addWidget(QtWidgets.QLabel("Subfolder:"))
        self.combo_subcategory_mat = QtWidgets.QComboBox()
        self.combo_subcategory_mat.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        subcat_layout.addWidget(self.combo_subcategory_mat)
        
        lib_layout.addLayout(cat_layout)
        lib_layout.addLayout(subcat_layout)
        lib_group.setLayout(lib_layout)
        layout.addWidget(lib_group)

        # 2. Search & Tools
        search_tools_layout = QtWidgets.QHBoxLayout()
        self.input_search_mat = QtWidgets.QLineEdit()
        self.input_search_mat.setPlaceholderText("Search materials...")
        self.btn_refresh_mat = QtWidgets.QPushButton("R")
        self.btn_refresh_mat.setFixedWidth(30)
        self.btn_generate_previews = QtWidgets.QPushButton("Generate Previews")
        self.btn_generate_previews.setToolTip("Gera miniaturas (bolinhas) para todos os materias desta pasta.")
        
        search_tools_layout.addWidget(self.input_search_mat)
        search_tools_layout.addWidget(self.btn_refresh_mat)
        search_tools_layout.addWidget(self.btn_generate_previews)
        layout.addLayout(search_tools_layout)

        # 3. List
        self.mat_list = QtWidgets.QListWidget()
        self.mat_list.setViewMode(QtWidgets.QListWidget.IconMode)
        self.mat_list.setIconSize(QtCore.QSize(130, 110))
        self.mat_list.setSpacing(10)
        self.mat_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        layout.addWidget(self.mat_list)

        # 4. Info & Action
        info_group = QtWidgets.QGroupBox("MATERIAL INFO")
        info_layout = QtWidgets.QVBoxLayout()
        self.lbl_mat_info_name = QtWidgets.QLabel("None selected")
        self.lbl_mat_info_name.setStyleSheet("font-weight: bold; color: #007acc;")
        self.btn_apply_mat = QtWidgets.QPushButton("APPLY TO SELECTED")
        self.btn_apply_mat.setObjectName("btnImport") # Use same style as Geo import
        self.btn_apply_mat.setFixedHeight(40)
        
        info_layout.addWidget(self.lbl_mat_info_name)
        info_layout.addWidget(self.btn_apply_mat)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Connections
        self.btn_refresh_mat.clicked.connect(self.refresh_materials)
        self.btn_generate_previews.clicked.connect(self.generate_mat_previews)
        self.combo_category_mat.currentIndexChanged.connect(self.on_category_changed_mat)
        self.combo_subcategory_mat.currentIndexChanged.connect(self.on_subcategory_changed_mat)
        self.input_search_mat.textChanged.connect(self.filter_materials)
        self.mat_list.itemClicked.connect(self.update_material_info_mat)
        self.mat_list.itemDoubleClicked.connect(self.on_material_double_clicked)
        self.mat_list.customContextMenuRequested.connect(self.open_material_context_menu)
        self.btn_apply_mat.clicked.connect(lambda: self.on_material_double_clicked(self.mat_list.currentItem()) if self.mat_list.currentItem() else None)

    def open_material_context_menu(self, pos):
        item = self.mat_list.itemAt(pos)
        if not item: return
        menu = QtWidgets.QMenu()
        apply_act = menu.addAction("Apply to Selection")
        slate_act = menu.addAction("Send to Slate Editor")
        compact_act = menu.addAction("Send to Compact Editor")
        
        action = menu.exec_(self.mat_list.mapToGlobal(pos))
        if not action: return
        
        mat_file = item.data(QtCore.Qt.UserRole)
        if action == apply_act:
            self.apply_material_logic(mat_file, mode="apply")
        elif action == slate_act:
            self.apply_material_logic(mat_file, mode="slate")
        elif action == compact_act:
            self.apply_material_logic(mat_file, mode="compact")

    def refresh_materials(self):
        self.combo_category_mat.blockSignals(True)
        self.combo_category_mat.clear()
        mat_path = self.settings.get('mat_lib_path', "")
        
        if mat_path and os.path.isdir(mat_path):
            try:
                categories = [d for d in os.listdir(mat_path) if os.path.isdir(os.path.join(mat_path, d))]
                self.combo_category_mat.addItems(sorted(categories))
            except Exception: pass
        
        self.combo_category_mat.blockSignals(False)
        if self.combo_category_mat.count() > 0: self.on_category_changed_mat()
        else: self.mat_list.clear()

    def on_category_changed_mat(self):
        cat = self.combo_category_mat.currentText()
        root = self.settings.get('mat_lib_path', "")
        if not cat or not root: return
        
        cat_path = os.path.join(root, cat)
        subfolders = [d for d in os.listdir(cat_path) if os.path.isdir(os.path.join(cat_path, d))]
        
        has_direct_mats = any(f.lower().endswith(".mat") for f in os.listdir(cat_path) if os.path.isfile(os.path.join(cat_path, f)))

        if has_direct_mats:
            self.combo_subcategory_mat.setVisible(False)
            self.populate_material_grid(cat_path)
        else:
            self.combo_subcategory_mat.blockSignals(True)
            self.combo_subcategory_mat.clear()
            self.combo_subcategory_mat.addItems(sorted(subfolders))
            self.combo_subcategory_mat.setVisible(True)
            self.combo_subcategory_mat.blockSignals(False)
            if subfolders: self.on_subcategory_changed_mat()
            else: self.mat_list.clear()

    def on_subcategory_changed_mat(self):
        cat = self.combo_category_mat.currentText()
        sub = self.combo_subcategory_mat.currentText()
        root = self.settings.get('mat_lib_path', "")
        if not cat or not sub or not root: return
        self.populate_material_grid(os.path.join(root, cat, sub))

    def populate_material_grid(self, folder):
        self.mat_list.clear()
        if not os.path.isdir(folder): return
        
        for f in os.listdir(folder):
            if f.lower().endswith(".mat"):
                full_p = os.path.join(folder, f)
                item = QtWidgets.QListWidgetItem(f)
                item.setData(QtCore.Qt.UserRole, full_p)
                thumb = self.find_thumbnail_for_mat(full_p)
                if thumb: item.setIcon(QtGui.QIcon(thumb))
                else: item.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon))
                self.mat_list.addItem(item)

    def update_material_info_mat(self, item):
        if not item: return
        self.lbl_mat_info_name.setText(item.text())

    def generate_mat_previews(self):
        count = self.mat_list.count()
        if count == 0: return
        
        msg = "Isso irá renderizar miniaturas para {} materiais. Pode levar alguns minutos. Deseja continuar?".format(count)
        if QtWidgets.QMessageBox.question(self, "Confirmar", msg) != QtWidgets.QMessageBox.Yes: return
        
        rt = pymxs.runtime
        prog = QtWidgets.QProgressDialog("Gerando miniaturas...", "Cancelar", 0, count, self)
        prog.setWindowModality(QtCore.Qt.WindowModal)
        prog.show()
        
        for i in range(count):
            if prog.wasCanceled(): break
            it = self.mat_list.item(i)
            path = it.data(QtCore.Qt.UserRole)
            name = it.text()
            out = os.path.splitext(path)[0] + ".jpg"
            
            prog.setLabelText("Renderizando: " + name)
            prog.setValue(i)
            # QtWidgets.QApplication.processEvents() # Estabilidade
            
            # Chama a função no MaxScript
            success = rt.NoobToolsCoreInst.renderMaterialPreview(path, name, out)
            if success:
                it.setIcon(QtGui.QIcon(out))
        
        prog.setValue(count)
        self.show_toast("Pre-visualizações geradas com sucesso!")

    def find_thumbnail_for_mat(self, mat_file):
        base = os.path.splitext(mat_file)[0]
        for ext in [".jpg", ".png", ".jpeg"]:
            if os.path.exists(base + ext): return base + ext
        return None

    def filter_materials(self, txt):
        txt = txt.lower()
        for i in range(self.mat_list.count()):
            it = self.mat_list.item(i)
            it.setHidden(txt not in it.text().lower())

    def on_material_double_clicked(self, item):
        mat_file = item.data(QtCore.Qt.UserRole)
        self.apply_material_logic(mat_file, mode="apply")

    def apply_material_logic(self, mat_file, mode="apply"):
        print("[NoobTools] Material Action: " + mode + " for " + mat_file)
        rt = pymxs.runtime
        try:
            # 1. Carregar a lib temporária
            mat_lib = rt.loadTempMaterialLibrary(mat_file)
            if not mat_lib or len(mat_lib) == 0:
                self.show_toast("Erro: Nenhum material no arquivo .mat")
                return
            
            first_mat = mat_lib[0]
            
            # Aplicar a TODA a seleção
            if "apply" in mode:
                sel = rt.selection
                if sel.count > 0:
                    for obj in sel:
                        obj.material = first_mat
                        # Forçar exibição da textura no viewport
                        try:
                            # 3ds Max: showTextureMap <material> <boolean>
                            rt.showTextureMap(obj.material, True) 
                        except: pass
                    
                    # Forçar atualização PESADA do viewport
                    rt.completeRedraw()
                    rt.redrawViews()
                    self.show_toast("Material aplicado a {} objetos!".format(sel.count))
                else:
                    self.show_toast("Selecione objetos no Max para aplicar.")

            # Abrir Editor
            if mode == "slate":
                rt.MatEditor.mode = rt.Name("advanced")
                rt.MatEditor.Open()
                sme = rt.sme
                if not sme.IsOpen(): sme.Open()
                view = sme.GetView(sme.ActiveView)
                if not view: view = sme.GetView(1)
                view.CreateNode(first_mat, rt.point2(0,0))
            
            elif mode == "compact":
                rt.MatEditor.mode = rt.Name("basic")
                rt.MeditMaterials[0] = first_mat
                rt.MatEditor.Open()
            
            elif mode == "apply_and_open": # Mantendo por compatibilidade se necessário internamente
                rt.MatEditor.Open()
                if rt.MatEditor.mode == rt.Name("advanced"):
                    sme = rt.sme
                    if not sme.IsOpen(): sme.Open()
                    view = sme.GetView(sme.ActiveView)
                    if not view: view = sme.GetView(1)
                    view.CreateNode(first_mat, rt.point2(0,0))
                else:
                    rt.MeditMaterials[0] = first_mat
                
        except Exception as e:
            self.show_toast("Erro Material: " + str(e))

        # --- TAB: SETTINGS ---
    def setup_settings_tab(self):
        layout_settings = QtWidgets.QVBoxLayout()
        self.tab_settings.setLayout(layout_settings)
        
        grupo_paths = QtWidgets.QGroupBox("PATHS")
        layout_paths = QtWidgets.QVBoxLayout()
        self.lbl_mat_path = QtWidgets.QLabel("Material Library Path:")
        layout_mat_browse = QtWidgets.QHBoxLayout()
        self.edt_mat_path = QtWidgets.QLineEdit()
        self.edt_mat_path.setText(self.settings.get('mat_lib_path', ""))
        self.btn_browse_mat = QtWidgets.QPushButton("...")
        self.btn_browse_mat.setFixedWidth(40)
        layout_mat_browse.addWidget(self.edt_mat_path); layout_mat_browse.addWidget(self.btn_browse_mat)
        layout_paths.addWidget(self.lbl_mat_path); layout_paths.addLayout(layout_mat_browse)
        grupo_paths.setLayout(layout_paths)
        layout_settings.addWidget(grupo_paths)

        grupo_backup = QtWidgets.QGroupBox("BACKUP")
        layout_backup = QtWidgets.QVBoxLayout()
        self.chk_autobackup = QtWidgets.QCheckBox("Auto-backup before operations")
        self.chk_autobackup.setChecked(self.settings.get('enable_autobackup', True))
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
        self.btn_browse_mat.clicked.connect(self.browse_mat_lib)
        self.chk_autobackup.stateChanged.connect(self.on_autobackup_changed)
        self.edt_mat_path.textChanged.connect(self.save_settings)
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
        for ext in ["*.max", "*.fbx", "*.obj", "*.3ds", "*.mat"]:
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

    def update_recent_favorites(self, folder):
        """Adiciona aos favoritos se for importado frequentemente."""
        if folder not in self.favorites:
            # Lógica simples: se importar, vira favorito temporário ou entra numa lista 'Recent'
            self.show_toast("Asset adicionado aos recentes.")

    def import_single_asset(self, folder, silent=False):
        main_file = self.find_main_file(folder)
        if not main_file:
            if not silent: self.show_toast("Erro: Nenhum arquivo 3D ou .mat encontrado.")
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
            elif ext.endswith(".mat"):
                rt.loadMaterialLibrary(main_file)
                self.show_toast("Material Library Carregada!")
            elif ext.endswith((".fbx", ".obj", ".3ds")):
                rt.importFile(main_file)

            refresh_asset_tracker()
            self.update_recent_favorites(folder)

            if self.chk_auto_layer.isChecked():
                lname = "".join(c for c in os.path.basename(folder) if c.isalnum() or c in ('_','-'))
                rt.NoobToolsCoreInst.addSelectionToLayer(lname)
            
            if self.chk_prefix.isChecked() and self.txt_prefix.text():
                rt.NoobToolsCoreInst.renameSelection(self.txt_prefix.text(), "")
            
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
            self.missing_assets = list(rt.NoobToolsCoreInst.getMissingAssets())
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
            count = pymxs.runtime.NoobToolsCoreInst.selectObjectsFromMissing(path)
            if count > 0: self.lbl_info_files.setText("Selecionados: {} objetos".format(count))
            else: QtWidgets.QMessageBox.information(self, "Info", "Mapa não aplicado a objetos 3D diretos.")
        except Exception: pass

    def strip_missing_paths(self):
        if not self.missing_assets: return
        self.create_backup()
        if QtWidgets.QMessageBox.question(self, "Confirmar", "Remover caminhos quebrados? (Irreversível)", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            try:
                count = pymxs.runtime.NoobToolsCoreInst.stripMissingPaths(self.missing_assets)
                self.scan_missing_files()
                QtWidgets.QMessageBox.information(self, "Sucesso", "Removidos: {}".format(count))
            except Exception: pass

    def run_scene_cleaner(self):
        print("[NoobTools] Running Scene Cleaner...")
        try:
            if hasattr(pymxs.runtime, "NoobToolsCoreInst"):
                res = list(pymxs.runtime.NoobToolsCoreInst.cleanScene())
                msg = "LIMPEZA CONCLUÍDA\n\n- Camadas removidas: {}\n- Grupos removidos: {}".format(int(res[0]), int(res[2]))
                QtWidgets.QMessageBox.information(self, "NoobFix - Cleaner", msg)
            else:
                self.show_toast("Erro: NoobToolsCore não carregado!")
        except Exception as e:
            log_error("Falha no Scene Cleaner: " + str(e))
            QtWidgets.QMessageBox.critical(self, "Erro", "Falha na limpeza:\n" + str(e))

    def run_scale_checker(self):
        print("[NoobTools] Checking Scene Scale...")
        try:
            if hasattr(pymxs.runtime, "NoobToolsCoreInst"):
                res = list(pymxs.runtime.NoobToolsCoreInst.checkSceneScale())
                msg = "UNIDADES DO SISTEMA\n\n- Unidade: {}\n- Fator de Escala: {}".format(res[0], res[1])
                QtWidgets.QMessageBox.information(self, "NoobFix - Scale", msg)
            else:
                self.show_toast("Erro: NoobToolsCore não carregado!")
        except Exception as e:
            log_error("Falha no Scale Checker: " + str(e))
            QtWidgets.QMessageBox.critical(self, "Erro", "Erro ao verificar escala:\n" + str(e))

    def convert_to_unc(self):
        self.create_backup()
        if QtWidgets.QMessageBox.question(self, "UNC", "Converter caminhos locais para Rede (UNC)?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            try:
                count = pymxs.runtime.NoobToolsCoreInst.convertToUNC()
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
            
            count = pymxs.runtime.NoobToolsCoreInst.collectFiles(save_dir)
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
                render_guess = pymxs.runtime.NoobToolsCoreInst.guessRenderer(f)
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
        search_terms = txt.lower().split()
        
        for i in range(self.asset_list.count()):
            it = self.asset_list.item(i)
            folder_path = it.data(QtCore.Qt.UserRole)
            name = os.path.basename(folder_path).lower()
            
            # Check Tags from metadata.json
            tags = []
            meta_path = os.path.join(folder_path, "metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        meta_data = json.load(f)
                        tags = [str(t).lower() for t in meta_data.get('tags', [])]
                except Exception: pass
            
            # Match Logic
            match = True
            for term in search_terms:
                if not (term in name or any(term in t for t in tags)):
                    match = False; break
            
            if mode != "ALL" and match:
                match = any(glob.glob(os.path.join(folder_path, "*"+mode)) for mode in [mode, mode.upper()])
            
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
        # AQUI ESTÁ A CORREÇÃO MÁGICA PARA FUNCIONAR EM QUALQUER VERSÃO!
        if IS_PYSIDE6:
            QtGui.QShortcut(QtGui.QKeySequence("F5"), self, self.refresh_ui)
            QtGui.QShortcut(QtGui.QKeySequence("Esc"), self, self.close)
        else:
            QtWidgets.QShortcut(QtGui.QKeySequence("F5"), self, self.refresh_ui)
            QtWidgets.QShortcut(QtGui.QKeySequence("Esc"), self, self.close)

    def browse_mat_lib(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Material Library Folder", self.settings.get('mat_lib_path', ""))
        if folder:
            self.edt_mat_path.setText(folder)
            self.settings['mat_lib_path'] = folder
            self.save_settings()
            self.refresh_materials()

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    self.settings = json.load(f)
                if hasattr(self, 'chk_autobackup'):
                    self.chk_autobackup.setChecked(self.settings.get('enable_autobackup', True))
                if hasattr(self, 'edt_mat_path'):
                    self.edt_mat_path.setText(self.settings.get('mat_lib_path', ""))
        except Exception: self.settings = {'enable_autobackup': True}

    def save_settings(self):
        try:
            if hasattr(self, 'chk_autobackup'):
                self.settings['enable_autobackup'] = self.chk_autobackup.isChecked()
            if hasattr(self, 'edt_mat_path'):
                self.settings['mat_lib_path'] = self.edt_mat_path.text()
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
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


    def closeEvent(self, e):
        self.save_config(); self.save_settings()
        if self.current_worker: self.current_worker.stop()
        if self.scanner_worker: self.scanner_worker.stop()
        e.accept()

