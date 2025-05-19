#!/usr/bin/env python3
#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from api.utils.log_utils import initRootLogger
from plugin import GlobalPluginManager
initRootLogger("fastapi_server")

import argparse
import logging
import os
import signal
import sys
import time
import traceback
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import uvicorn

from api import settings
from api.fastapi_app import app
from api.db.db_models import init_database_tables as init_web_db
from api.db.init_data import init_web_data
from api.db.runtime_config import RuntimeConfig
from api.db.services.document_service import DocumentService
from api.versions import get_ragflow_version
from api.utils import show_configs
from rag.settings import print_rag_settings
from rag.utils.redis_conn import RedisDistributedLock

stop_event = threading.Event()

RAGFLOW_DEBUGPY_LISTEN = int(os.environ.get('RAGFLOW_DEBUGPY_LISTEN', "0"))

def update_progress():
    """
    Background task to update document processing progress.
    Uses Redis lock to avoid race conditions in distributed deployments.
    """
    lock_value = str(uuid.uuid4())
    redis_lock = RedisDistributedLock("update_progress", lock_value=lock_value, timeout=60)
    logging.info(f"update_progress lock_value: {lock_value}")
    
    while not stop_event.is_set():
        try:
            if redis_lock.acquire():
                DocumentService.update_progress()
                redis_lock.release()
            stop_event.wait(6)
        except Exception:
            logging.exception("update_progress exception")
        finally:
            redis_lock.release()

def signal_handler(sig, frame):
    """
    Handle interrupt signals to shut down gracefully.
    """
    logging.info("Received interrupt signal, shutting down...")
    stop_event.set()
    time.sleep(1)
    sys.exit(0)

def main():
    """
    Main entry point for the FastAPI server.
    """
    logging.info(r"""
        ____   ___    ______ ______ __               
       / __ \ /   |  / ____// ____// /____  _      __
      / /_/ // /| | / / __ / /_   / // __ \| | /| / /
     / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ / 
    /_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/                             

    """)
    logging.info(f'RAGFlow version: {get_ragflow_version()}')
    logging.info(f'project base: {os.path.dirname(os.path.abspath(__file__))}')
    
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", default=False, help="RAGFlow version", action="store_true"
    )
    parser.add_argument(
        "--debug", default=False, help="debug mode", action="store_true"
    )
    args = parser.parse_args()
    
    if args.version:
        print(get_ragflow_version())
        sys.exit(0)
    
    # Initialize configurations
    show_configs()
    settings.init_settings()
    print_rag_settings()
    
    # Configure debugpy if enabled
    if RAGFLOW_DEBUGPY_LISTEN > 0:
        logging.info(f"debugpy listen on {RAGFLOW_DEBUGPY_LISTEN}")
        import debugpy
        debugpy.listen(("0.0.0.0", RAGFLOW_DEBUGPY_LISTEN))
    
    # Initialize database
    init_web_db()
    init_web_data()
    
    # Set runtime configuration
    RuntimeConfig.DEBUG = args.debug
    if RuntimeConfig.DEBUG:
        logging.info("run on debug mode")
    
    RuntimeConfig.init_env()
    RuntimeConfig.init_config(JOB_SERVER_HOST=settings.HOST_IP, HTTP_PORT=settings.HOST_PORT)
    
    # Load plugins
    GlobalPluginManager.load_plugins()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start progress update thread
    thread = ThreadPoolExecutor(max_workers=1)
    thread.submit(update_progress)
    
    # Start FastAPI server
    try:
        logging.info("RAGFlow FastAPI server starting...")
        uvicorn.run(
            app, 
            host=settings.HOST_IP,
            port=settings.HOST_PORT,
            log_level="info" if not RuntimeConfig.DEBUG else "debug",
            reload=RuntimeConfig.DEBUG
        )
    except Exception:
        traceback.print_exc()
        stop_event.set()
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGKILL)

if __name__ == "__main__":
    main() 