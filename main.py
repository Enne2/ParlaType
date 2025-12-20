#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ParlaType - Speech-to-Text Virtual Keyboard (Italian Edition)
=============================================================

Entry point for the modularized ParlaType application.
"""

import sys
from parlatype.core.config import request_lock, init_config
from parlatype.app import ParlaTypeApp

if __name__ == "__main__":
    # Initialize configuration and environment variables
    init_config()

    # Ensure single instance
    lock_file = request_lock()
    if not lock_file:
        print("ParlaType is already running.")
        sys.exit(1)

    # Launch the application
    app = ParlaTypeApp()
    sys.exit(app.run(sys.argv))
