import logging

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from mop.ui.creation import CreationPanel
from mop.ui.module import ModulePanel
from mop.ui.rig import RigPanel
from mop.ui.settings import get_settings
from mop.ui.signals import clear_all_signals, publish, subscribe
from mop.vendor.Qt import QtWidgets, QtCore

logger = logging.getLogger(__name__)


class mopWindow(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """The main window of the mop GUI."""

    ui_name = "mop_main_window"

    def __init__(self, parent=None):
        super(mopWindow, self).__init__(parent)
        self.setObjectName(self.ui_name)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle("Master Of Puppets")

        self.setDockNestingEnabled(True)

        self.creation_panel = CreationPanel()
        self.module_panel = ModulePanel()
        self.rig_panel = RigPanel()

        self.setCentralWidget(self.rig_panel)

        for dock in [self.creation_panel, self.module_panel]:
            dock.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
            dock.setFeatures(
                QtWidgets.QDockWidget.DockWidgetMovable
                | QtWidgets.QDockWidget.DockWidgetFloatable
            )

        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.creation_panel)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.module_panel)

        self.load_settings()

    def save_settings(self):
        name = self.objectName()
        settings = get_settings()

        settings.setValue("%s/state" % name, self.saveState())
        settings.setValue("%s/floating" % name, self.isFloating())
        settings.setValue("%s/area" % name, self.dockArea())
        settings.setValue("%s/geometry" % name, self.saveGeometry())

        publish("save-settings")
        logger.info("Saved mop settings.")

    def load_settings(self):
        name = self.objectName()
        settings = get_settings()

        state = settings.value("%s/state" % name)
        if state:
            self.restoreState(state)

        geometry = settings.value("%s/geometry" % name)
        if geometry:
            self.restoreGeometry(geometry)

        publish("load-settings")
        logger.info("Loaded mop settings.")

    def floatingChanged(self, floating):
        self.save_settings()

    def dockCloseEventTriggered(self):
        self.save_settings()
        clear_all_signals()

    def close(self):
        self.save_settings()
        clear_all_signals()
        super(mopWindow, self).close()
