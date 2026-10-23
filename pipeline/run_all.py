"""Run the whole pipeline in order from the repository root:  python pipeline/run_all.py"""
import runpy, sys
from pathlib import Path
here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
for stage in ['build_data', 'value_shares', 'validate', 'overlaps', 'decomposition', 'splice', 'benchmark', 'revision', 'episodes', 'noise', 'inference', 'splice_extra', 'reliability', 'diagnosis', 'sources', 'tests', 'window_contrast', 'charts', 'charts_reliability', 'paper_numbers']:
    print(f'\n========== {stage}.py ==========')
    runpy.run_path(str(here / f'{stage}.py'), run_name='__main__')
