import maya.cmds as cmds

from icarus.ui.createmodule import CreateModulePanel
from icarus.ui.modules import ModulesPanel
from icarus.ui.settings import SettingsPanel
from icarus.vendor.Qt import QtCore


if '_INSTANCES' not in globals():
    _INSTANCES = {}


def show():
    """Run the Icarus GUI."""
    settings = get_settings()
    for cls in [CreateModulePanel, ModulesPanel, SettingsPanel]:
        instance = cls()

        name = instance.objectName()

        # Deleting the workspace will delete the
        # panel.
        # This is done in case the GUI is already opened,
        # as Maya commands will crash if two workspaces
        # with the same name exist.
        close_instance_workspace(name)

        kwargs = {}
        floating = settings.value('%s/floating' % name)
        if floating is not None:
            kwargs['floating'] = floating
        area = settings.value('%s/area' % name)
        if area is not None:
            kwargs['area'] = area
        g = settings.value('%s/geometry' % name)
        if g is not None:
            kwargs['x'] = g.x()
            kwargs['y'] = g.y()
            kwargs['width'] = g.width()
            kwargs['height'] = g.height()
        instance.show(
            dockable=True,
            **kwargs
        )
        _INSTANCES[name] = instance


def close():
    """Close all Icarus panels.

    .. note::

        Panel settings will be saved.
    """
    save_settings()
    for name, instance in _INSTANCES.items():
        instance.close()
        close_instance_workspace(name)


def close_instance_workspace(name):
    """Close an Icarus panel workspace.

    :param instance: Instance to close.
    :type instance: PySide2.QtWidgets.QWidget
    """
    workspace = get_workspace_name(name)
    if cmds.workspaceControl(workspace, exists=True):
        cmds.deleteUI(workspace, control=True)
        if name in _INSTANCES:
            del _INSTANCES[name]


def get_settings():
    """Return Icarus application settings."""
    return QtCore.QSettings(
        QtCore.QSettings.IniFormat,
        QtCore.QSettings.UserScope,
        'Holistic Coders',
        'Icarus',
    )


def get_workspace_name(name):
    """Return the name of the panel associated workspace.

    :param name: Name of the panel you want the workspace of.
    :type name: str
    :rtype: str
    """
    return name + 'WorkspaceControl'


def load_settings():
    """Load previously stored settings on the GUI.

    .. note::

        The GUI must already been running for this method
        to work.
    """
    settings = get_settings()
    for name, instance in _INSTANCES.iteritems():
        kwargs = {}
        floating = settings.value('%s/floating' % name)
        if floating is not None:
            kwargs['floating'] = floating
        area = settings.value('%s/area' % name)
        if area is not None:
            kwargs['area'] = area
        g = settings.value('%s/geometry' % name)
        if g is not None:
            kwargs['x'] = g.x()
            kwargs['y'] = g.y()
            kwargs['width'] = g.width()
            kwargs['height'] = g.height()
        instance.setDockableParameters(
            dockable=True,
            **kwargs
        )
        if instance.isFloating():
            instance.resize(w, h)
            instance.move(x, y)


def save_settings():
    """Save the current GUI session settings.

    The following settings are saved for each widget:

        * floating
        * area
        * geometry
    """
    settings = get_settings()
    for name, instance in _INSTANCES.iteritems():
        settings.setValue('%s/floating' % name, instance.isFloating())
        settings.setValue('%s/area' % name, instance.dockArea())
        if instance.isFloating():
            geometry = instance.window().geometry()
        else:
            # Get the dock geometry.
            geometry = instance.parent().geometry()
        settings.setValue('%s/geometry' % name, geometry)

