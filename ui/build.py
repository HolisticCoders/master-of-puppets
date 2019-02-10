import maya.cmds as cmds

from icarus.ui.settings import get_settings
from icarus.ui.window import IcarusWindow


def show():
    """Run the Icarus GUI."""
    window = IcarusWindow()
    name = IcarusWindow.ui_name

    # Make sure the workspace is not shown, nor exists.
    close()

    settings = get_settings()

    kwargs = {}
    floating = settings.value('%s/floating' % name)
    if floating is not None:
        kwargs['floating'] = floating

    area = settings.value('%s/area' % name)
    if area is not None:
        kwargs['area'] = area

    window.show(dockable=True, **kwargs)


def close():
    """Close icarus GUI."""
    if is_running():
        cmds.workspaceControl(get_workspace(), edit=True, close=True)
        cmds.deleteUI(get_workspace(), control=True)


def is_running():
    """Return ``True`` if Icarus GUI is currently opened.

    :rtype: bool
    """
    return cmds.workspaceControl(get_workspace(), exists=True)


def get_workspace():
    """Return the name of the Icarus workspace control.

    :rtype: str
    """
    return IcarusWindow.ui_name + 'WorkspaceControl'
