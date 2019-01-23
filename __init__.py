import sys
import os

import icarus.internals

# add vendor folder to PYTHONPATH
curr_dir = os.path.dirname(__file__)
vendor = os.path.join(curr_dir, 'vendor')
sys.path.append(vendor)

increment_version = icarus.internals.increment_version
incremental_save = icarus.internals.incremental_save
save_publish = icarus.internals.save_publish

