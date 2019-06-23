import site

site.addsitedir("/path/to/master-of-puppets/")

# It is essential to set this variable to `True` for dynamic
# reloading through the `Reload mop` menu item.
sys.dont_write_bytecode = True

from maya import utils

import mop.ui.menu

utils.executeDeferred(mop.ui.menu.build_menu)
