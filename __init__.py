import sys
import os

import mop.internals

# add vendor folder to PYTHONPATH
curr_dir = os.path.dirname(__file__)
vendor = os.path.join(curr_dir, "vendor")
sys.path.append(vendor)

increment_version = mop.internals.increment_version
incremental_save = mop.internals.incremental_save
save_publish = mop.internals.save_publish
