import maya.cmds as cmds

import mop.ui.commands


mop_MENU = 'mop_menu'

MENU_ITEMS = [
    {
        'name': 'mop_increment_menu_item',
        'command': 'import mop;mop.incremental_save()',
        'label': 'Incremental Save',
    },
    {
        'name': 'mop_open_menu_item',
        'command': 'from mop.ui.commands import open_mop;open_mop()',
        'label': 'Open MOP',
    },
    {
        'name': 'mop_open_parent_spaces_menu_item',
        'command': 'from mop.ui.commands import open_parent_spaces;open_parent_spaces()',
        'label': 'Open Parent Spaces',
    },
    {
        'name': 'mop_open_facs_editor_menu_item',
        'command': 'from mop.ui.commands import open_facs_editor;open_facs_editor()',
        'label': 'Open FACS Editor',
    },
    {
        'name': 'mop_build_menu_item',
        'command': 'from mop.ui.commands import build_rig;build_rig()',
        'label': 'Build Rig',
    },
    {
        'name': 'mop_unbuild_menu_item',
        'command': 'from mop.ui.commands import unbuild_rig;unbuild_rig()',
        'label': 'Unbuild Rig',
    },
    {
        'name': 'mop_reload_menu_item',
        'command': 'from mop.ui.commands import reload_mop;reload_mop()',
        'label': 'Reload MOP',
    },
]


def build_menu():
    """Create the mop menu.

    It contains four items:

        * Reload mop: Reloads the entire mop package.
        * Open mop: Opens the mop GUI.
        * Build Rig: Builds the rig contained in the scene.
        * Unbuild Rig: Unbuilds the rig contained in the scene.
    """
    if not cmds.menu(mop_MENU, query=True, exists=True):
        cmds.menu(mop_MENU, label='MOP', parent='MayaWindow', tearOff=False)

    for data in MENU_ITEMS:
        name = data.pop('name')
        cmds.menuItem(
            name,
            parent=mop_MENU,
            **data
        )

