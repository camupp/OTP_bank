"""Current independent verification entry point; writes only finance checks.
The initial cash/core verification is retained in the coordinator archive.
"""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('delta_check.py')), run_name='__main__')
