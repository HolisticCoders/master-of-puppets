import maya.cmds as cmds

import icarus.ui.commands


ICARUS_MENU = 'icarus_menu'
ICARUS_RELOAD_MI = 'icarus_reload_menu_item'
ICARUS_OPEN_MI = 'icarus_open_menu_item'
ICARUS_BUILD_MI = 'icarus_build_menu_item'
ICARUS_UNBUILD_MI = 'icarus_unbuild_menu_item'

MENU_ITEMS = {
    ICARUS_RELOAD_MI: {
        'command': 'from icarus.ui.commands import reload_icarus;reload_icarus()',
        'label': 'Reload Icarus',
    },
    ICARUS_OPEN_MI: {
        'command': 'from icarus.ui.commands import open_icarus;open_icarus()',
        'label': 'Open Icarus',
    },
    ICARUS_BUILD_MI: {
        'command': 'from icarus.ui.commands import build_rig;build_rig()',
        'label': 'Build Rig',
    },
    ICARUS_UNBUILD_MI: {
        'command': 'from icarus.ui.commands import unbuild_rig;unbuild_rig()',
        'label': 'Unbuild Rig',
    },
}


def build_menu():
    """Create the Icarus menu.

    It contains four items:

        * Reload Icarus: Reloads the entire Icarus package.
        * Open Icarus: Opens the Icarus GUI.
        * Build Rig: Builds the rig contained in the scene.
        * Unbuild Rig: Unbuilds the rig contained in the scene.
    """
    if not cmds.menu(ICARUS_MENU, query=True, exists=True):
        cmds.menu(ICARUS_MENU, label='Icarus', parent='MayaWindow', tearOff=False)

    for label, data in MENU_ITEMS.iteritems():
        cmds.menuItem(
            parent=ICARUS_MENU,
            **data
        )

