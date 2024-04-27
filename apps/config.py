# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
import random
import string
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import QueuePool
import time

class Config(object):

    basedir = os.path.abspath(os.path.dirname(__file__))

    # Assets Management
    ASSETS_ROOT = os.getenv('ASSETS_ROOT', '/static/assets')

    # Set up the App SECRET_KEY
    SECRET_KEY = os.getenv('SECRET_KEY', ''.join(random.choice(string.ascii_lowercase) for _ in range(32)))

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DB_ENGINE = os.getenv('DB_ENGINE', None)
    DB_USERNAME = os.getenv('DB_USERNAME', None)
    DB_PASS = os.getenv('DB_PASS', None)
    DB_HOST = os.getenv('DB_HOST', None)
    DB_PORT = os.getenv('DB_PORT', None)
    DB_NAME = os.getenv('DB_NAME', None)

    USE_SQLITE = True 

    # Set up a Relational DBMS if available
    if DB_ENGINE and DB_NAME and DB_USERNAME:
        URI_TEMPLATE = '{}://{}:{}@{}:{}/{}'
        MAX_RETRIES = 5  # Maximum number of connection attempts
        RETRY_WAIT = 5   # Seconds to wait between retries

        for attempt in range(MAX_RETRIES):
            try:
                # Connection pooling configuration
                engine = create_engine(
                    URI_TEMPLATE.format(DB_ENGINE, DB_USERNAME, DB_PASS, DB_HOST, DB_PORT, DB_NAME),
                    poolclass=QueuePool,
                    pool_size=10,
                    max_overflow=5,
                    pool_timeout=30,  # Adjust timeout to your needs
                    pool_recycle=3600  # Recycles connections after one hour
                )

                # If connection is successful, set SQLAlchemy URI and disable SQLite
                SQLALCHEMY_DATABASE_URI = str(engine.url)
                USE_SQLITE = False
                break
            except OperationalError as e:
                print(f'> Connection attempt {attempt + 1} failed: {e}')
                if attempt < MAX_RETRIES - 1:
                    print(f'> Retrying in {RETRY_WAIT} seconds...')
                    time.sleep(RETRY_WAIT)
                else:
                    print('> Fallback to SQLite')

    if USE_SQLITE:
        # This will create a file in <app> folder
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')

class ProductionConfig(Config):
    DEBUG = False

    # Security
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_DURATION = 3600


class DebugConfig(Config):
    DEBUG = True


# Load all possible configurations
config_dict = {
    'Production': ProductionConfig,
    'Debug'     : DebugConfig
}
