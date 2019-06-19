import maya.cmds as cmds

from mop.ui.settings import get_settings
from mop.ui.window import mopWindow


def show():
    """Run the mop GUI."""
    window = mopWindow()
    name = mopWindow.ui_name

    # Make sure the workspace is not shown, nor exists.
    close()

    settings = get_settings()

    kwargs = {}
    floating = settings.value("%s/floating" % name)
    if floating is not None:
        kwargs["floating"] = floating

    area = settings.value("%s/area" % name)
    if area is not None:
        kwargs["area"] = area

    window.show(dockable=True, **kwargs)


def close():
    """Close mop GUI."""
    if is_running():
        cmds.workspaceControl(get_workspace(), edit=True, close=True)
        cmds.deleteUI(get_workspace(), control=True)


def is_running():
    """Return ``True`` if mop GUI is currently opened.

    :rtype: bool
    """
    return cmds.workspaceControl(get_workspace(), exists=True)


def get_workspace():
    """Return the name of the mop workspace control.

    :rtype: str
    """
    return mopWindow.ui_name + "WorkspaceControl"
