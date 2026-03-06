# -*- coding: utf-8 -*-
import os
import tempfile
import logging

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
