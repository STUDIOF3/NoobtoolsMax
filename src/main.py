# -*- coding: utf-8 -*-
import sys
import os
import pymxs

def get_max_main_window():
    from src.utils.qt_compat import QtWidgets
    try:
        app = QtWidgets.QApplication.instance()
        if not app: return None
        try: import qtmax; return qtmax.GetQMaxMainWindow()
        except: pass
        try: import MaxPlus; return MaxPlus.GetQMaxMainWindow()
        except: pass
        for w in app.topLevelWidgets():
            if isinstance(w, QtWidgets.QMainWindow) and ('3ds Max' in w.windowTitle() or 'Autodesk' in w.windowTitle()): return w
        return app.activeWindow()
    except Exception: return None

import importlib

def reload_modules():
    """Força o recarregamento dos módulos para garantir que atualizações entrem em vigor no Max."""
    to_reload = [
        "src.utils.logger",
        "src.utils.qt_compat",
        "src.core.threads",
        "src.ui.style",
        "src.ui.widgets",
        "src.ui.main_window"
    ]
    for mod_name in to_reload:
        if mod_name in sys.modules:
            try:
                importlib.reload(sys.modules[mod_name])
            except Exception: pass

_noob_tools_instance = None

def main():
    global _noob_tools_instance
    reload_modules()
    
    # Importar aqui dentro para garantir que pegamos os módulos recém-recarregados
    from src.utils.logger import log_error, log_info
    from src.ui.main_window import NoobToolsWindow
    from src.utils.qt_compat import QtWidgets

    try:
        # Load MaxScript Core
        src_dir = os.path.dirname(os.path.abspath(__file__))
        ms_core_path = os.path.join(src_dir, "maxscript", "noob_core.ms")
        
        # fallback just in case __file__ behaves weirdly in maxscript
        if not os.path.exists(ms_core_path):
            try:
                ms_core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "maxscript", "noob_core.ms")
            except:
                pass

        if os.path.exists(ms_core_path):
            pymxs.runtime.filein(ms_core_path)
            log_info("MaxScript Core loaded successfully.")
        else:
            log_error(f"MaxScript Core not found at: {ms_core_path}")

        if _noob_tools_instance is not None:
            try:
                _noob_tools_instance.close()
                _noob_tools_instance.deleteLater()
            except Exception: pass
            
        mw = get_max_main_window()
        _noob_tools_instance = NoobToolsWindow(parent=mw)
        _noob_tools_instance.show()
    except Exception as e:
        log_error(f"Erro ao iniciar o plugin: {str(e)}")

if __name__ == "__main__":
    main()
