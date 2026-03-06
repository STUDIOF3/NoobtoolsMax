# -*- coding: utf-8 -*-
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    IS_PYSIDE6 = True
except ImportError:
    try:
        from PySide2 import QtWidgets, QtCore, QtGui
        IS_PYSIDE6 = False
    except ImportError:
        try:
            from PySide import QtWidgets, QtCore, QtGui
            IS_PYSIDE6 = False
        except ImportError:
            QtWidgets = QtCore = QtGui = None
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
