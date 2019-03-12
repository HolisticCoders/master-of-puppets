import maya.cmds as cmds

from facseditor.window import FACSWindow


def show():
    """Run the FACS editor GUI."""
    window = FACSWindow()
    name = FACSWindow.ui_name

    # Make sure the workspace is not shown, nor exists.
    close()
    window.show(dockable=True)


def close():
    """Close icarus GUI."""
    if is_running():
        cmds.workspaceControl(get_workspace(), edit=True, close=True)
        cmds.deleteUI(get_workspace(), control=True)


def is_running():
    """Return ``True`` if FACS GUI is currently opened.

    :rtype: bool
    """
    return cmds.workspaceControl(get_workspace(), exists=True)


def get_workspace():
    """Return the name of the FACS workspace control.

    :rtype: str
    """
    return FACSWindow.ui_name + 'WorkspaceControl'

