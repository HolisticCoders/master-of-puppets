import sys
import os

# add vendor folder to PYTHONPATH
curr_dir = os.path.dirname(__file__)
vendor = os.path.join(curr_dir, 'vendor')
sys.path.append(vendor)
