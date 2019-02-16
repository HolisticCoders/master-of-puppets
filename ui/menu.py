import maya.cmds as cmds

import icarus.ui.commands


ICARUS_MENU = 'icarus_menu'

MENU_ITEMS = [
    {
        'name': 'icarus_increment_menu_item',
        'command': 'import icarus;icarus.incremental_save()',
        'label': 'Incremental Save',
    },
    {
        'name': 'icarus_open_menu_item',
        'command': 'from icarus.ui.commands import open_icarus;open_icarus()',
        'label': 'Open Icarus',
    },
    {
        'name': 'icarus_open_parent_spaces_menu_item',
        'command': 'from icarus.ui.commands import open_parent_spaces;open_parent_spaces()',
        'label': 'Open Parent Spaces',
    },
    {
        'name': 'icarus_build_menu_item',
        'command': 'from icarus.ui.commands import build_rig;build_rig()',
        'label': 'Build Rig',
    },
    {
        'name': 'icarus_unbuild_menu_item',
        'command': 'from icarus.ui.commands import unbuild_rig;unbuild_rig()',
        'label': 'Unbuild Rig',
    },
    {
        'name': 'icarus_reload_menu_item',
        'command': 'from icarus.ui.commands import reload_icarus;reload_icarus()',
        'label': 'Reload Icarus',
    },
]


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

    for data in MENU_ITEMS:
        name = data.pop('name')
        cmds.menuItem(
            name,
            parent=ICARUS_MENU,
            **data
        )

