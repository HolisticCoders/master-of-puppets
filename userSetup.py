# It is essential to set this variable to `True` for dynamic
# reloading through the `Reload mop` menu item.
import sys

sys.dont_write_bytecode = True

import maya.cmds as cmds

cmds.evalDeferred("import mop.ui.menu; mop.ui.menu.build_menu()")
