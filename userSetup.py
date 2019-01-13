import sys
# It is essential to set this variable to `True` for dynamic
# reloading through the `Reload Icarus` menu item.
sys.dont_write_bytecode = True


from maya import utils

import icarus.ui.menu

utils.executeDeferred(icarus.ui.menu.build_menu)
