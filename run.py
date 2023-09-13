# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
from flask_migrate import Migrate
from flask_minify import Minify
from apps import create_app, db

# WARNING: Don't run with debug turned on in production!
DEBUG = (os.getenv('DEBUG', 'False') == 'True')

app = create_app()

Migrate(app, db)

if not DEBUG:
    Minify(app=app, html=True, js=False, cssless=False)
    
if DEBUG:
    app.logger.info('DEBUG            = ' + str(DEBUG))
    app.logger.info('Page Compression = ' + ('FALSE' if DEBUG else 'TRUE'))
    app.logger.info('DBMS             = ' + os.getenv('DATABASE_URL', 'sqlite:///db.sqlite'))

if __name__ == "__main__":
    app.run()
