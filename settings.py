#!/usr/bin/python3
"""Compatibility entry point for the new Neon Studio control panel."""
import os
from pathlib import Path
os.execv('/usr/bin/python3',['/usr/bin/python3',str(Path(__file__).resolve().parent/'control-center.py')])
