import site
import os

import mop.internals

# add vendor folder to PYTHONPATH
curr_dir = os.path.dirname(__file__)
vendor = os.path.abspath(os.path.join(curr_dir, "..", "vendor"))
site.addsitedir(vendor)

increment_version = mop.internals.increment_version
incremental_save = mop.internals.incremental_save
save_publish = mop.internals.save_publish
