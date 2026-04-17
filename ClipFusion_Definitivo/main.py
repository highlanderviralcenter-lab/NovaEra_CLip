#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main_gui import ClipFusionApp

if __name__ == "__main__":
    app = ClipFusionApp()
    app.run()
