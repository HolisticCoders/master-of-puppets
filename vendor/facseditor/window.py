from collections import OrderedDict
from functools import wraps
import json
import logging

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.cmds as cmds

from icarus.vendor.Qt import QtWidgets, QtCore, QtGui
import facseditor.core

logger = logging.getLogger(__name__)


def undoable(func):
    """Decorated function will execute in one undo chunk."""

    @wraps(func)
    def wrapped(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)

    return wrapped


class FACSWindow(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
    """The main window of the Icarus GUI."""

    ui_name = 'facs_main_window'

    def __init__(self, parent=None):
        super(FACSWindow, self).__init__(parent)
        self.setObjectName(self.ui_name)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('FACS Editor')

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QtWidgets.QVBoxLayout()
        lists_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(lists_layout)
        central_widget.setLayout(main_layout)

        # FACS action units part
        facs_group = QtWidgets.QGroupBox('FACS Action units')
        lists_layout.addWidget(facs_group)

        facs_layout = QtWidgets.QVBoxLayout()
        facs_group.setLayout(facs_layout)
        self.action_units_list = QtWidgets.QListView()
        self.action_units_model = ActionUnitsModel()
        self.action_units_list.setModel(self.action_units_model)
        self.action_units_model.setStringList(facseditor.core.get_action_units())
        self.action_units_model.dataChanged.connect(self.action_units_data_changed)
        self.action_units_list.selectionModel().selectionChanged.connect(
            self.facs_selection_changed
        )
        self.action_units_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        ) 
        self.action_units_list.setDragEnabled(True)
        self.action_units_list.setAcceptDrops(True)
        self.action_units_list.setDropIndicatorShown(True)

        facs_layout.addWidget(self.action_units_list)
        facs_actions_layout = QtWidgets.QHBoxLayout()
        facs_layout.addLayout(facs_actions_layout)

        facs_add_button = QtWidgets.QPushButton('Add')
        facs_add_button.released.connect(self.add_action_unit)
        facs_actions_layout.addWidget(facs_add_button)
        facs_remove_button = QtWidgets.QPushButton('Remove')
        facs_remove_button.released.connect(self.remove_action_units)
        facs_actions_layout.addWidget(facs_remove_button)
        self.facs_edit_button = QtWidgets.QPushButton('Edit')
        self.facs_edit_button.released.connect(self.edit_action_unit)
        facs_actions_layout.addWidget(self.facs_edit_button)
        self.facs_finish_edit_button = QtWidgets.QPushButton('Finish Edit')
        self.facs_finish_edit_button.released.connect(self.finish_edit_action_unit)

        self.update_edit_buttons()

        facs_actions_layout.addWidget(self.facs_finish_edit_button)

        # Controllers part
        controllers_group = QtWidgets.QGroupBox('Controllers')
        lists_layout.addWidget(controllers_group)

        controllers_layout = QtWidgets.QVBoxLayout()
        controllers_group.setLayout(controllers_layout)
        self.controllers_list = QtWidgets.QListView()
        self.controllers_model = QtCore.QStringListModel()
        self.controllers_list.setModel(self.controllers_model)
        self.controllers_list.selectionModel().selectionChanged.connect(
            self.controllers_selection_changed
        )
        self.controllers_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        controllers_layout.addWidget(self.controllers_list)
        controllers_actions_layout = QtWidgets.QHBoxLayout()
        controllers_layout.addLayout(controllers_actions_layout)

        controllers_add_button = QtWidgets.QPushButton('Add Selected')
        controllers_add_button.released.connect(self.add_controllers_to_action_unit)
        controllers_actions_layout.addWidget(controllers_add_button)
        controllers_remove_button = QtWidgets.QPushButton('Remove')
        controllers_remove_button.released.connect(self.remove_controllers_from_action_unit)
        controllers_actions_layout.addWidget(controllers_remove_button)

        select_facs_button = QtWidgets.QPushButton('Select FACS Control')
        select_facs_button.released.connect(self._select_facs_control)
        main_layout.addWidget(select_facs_button)

        facseditor.core.ensure_facs_node_exists()

    def update_edit_buttons(self):
        if facseditor.core.is_editing():
            self.facs_edit_button.setEnabled(False)
            self.facs_finish_edit_button.setEnabled(True)
        else:
            self.facs_edit_button.setEnabled(True)
            self.facs_finish_edit_button.setEnabled(False)

    def facs_selection_changed(self):
        self.update_controllers_model()

    def update_controllers_model(self):
        if not self.action_units_list.selectionModel().selectedIndexes():
            controllers = []
        else:
            current_action_unit = self.action_units_list.selectionModel().currentIndex().data()
            action_units_dict = facseditor.core.get_action_units_dict()
            controllers = action_units_dict[current_action_unit]
        self.controllers_model.setStringList(controllers)

    def update_action_units_model(self):
        self.action_units_model.setStringList(facseditor.core.get_action_units())

    def controllers_selection_changed(self):
        controllers_names = [c.data() for c in self.controllers_list.selectionModel().selectedIndexes()]
        cmds.select(controllers_names)

    @undoable
    def add_action_unit(self):
        facseditor.core.add_action_unit()
        self.update_action_units_model()

    @undoable
    def remove_action_units(self):
        action_units = [a.data() for a in self.action_units_list.selectionModel().selectedIndexes()]
        facseditor.core.remove_action_units(action_units)
        self.update_action_units_model()

    @undoable
    def move_action_unit(self, new_key, new_index):
        return facseditor.core.move_action_unit(new_key, new_index)

    def action_units_data_changed(self, topLeft, bottomRight, roles):
        new_index = topLeft.row()
        new_key = topLeft.data()

        if roles[0] == QtCore.Qt.DisplayRole:
            new_dict = self.move_action_unit(new_key, new_index)

        elif roles[0] == QtCore.Qt.EditRole:
            new_dict = facseditor.core.rename_action_unit(new_index, new_key)
        facs_node = facseditor.core.ensure_facs_node_exists()
        cmds.setAttr(
            facs_node + '.actionUnits',
            json.dumps(new_dict),
            type='string'
        )
        self.update_action_units_model()

    @undoable
    def edit_action_unit(self):
        if not self.action_units_list.selectionModel().selectedIndexes():
            return
        cmds.playbackOptions(min=0, max=10)
        last_action_unit = self.action_units_list.selectionModel().currentIndex().data()
        facseditor.core.edit_action_unit(last_action_unit)
        self.update_edit_buttons()
        self.update_action_units_model()

    @undoable
    def finish_edit_action_unit(self):
        facseditor.core.finish_edit()
        self.update_edit_buttons()
        self.update_action_units_model()

    @undoable
    def add_controllers_to_action_unit(self):
        if not self.action_units_list.selectionModel().selectedIndexes():
            return
        last_action_unit = self.action_units_list.selectionModel().currentIndex().data()
        facseditor.core.add_controllers_to_action_unit(last_action_unit)
        self.update_controllers_model()

    @undoable
    def remove_controllers_from_action_unit(self):
        last_action_unit = self.action_units_list.selectionModel().currentIndex().data()
        selected_controllers = [c.data() for c in self.controllers_list.selectionModel().selectedIndexes()]
        facseditor.core.remove_controllers_from_action_unit(last_action_unit, selected_controllers)
        self.update_controllers_model()

    def _select_facs_control(self):
        cmds.select(facseditor.core.ensure_facs_node_exists(), replace=True)


class ActionUnitsModel(QtCore.QStringListModel):
    def data(self, index, role):
        """Color the Action unit that's being edited."""
        if role == QtCore.Qt.BackgroundRole:
            if index.data() == facseditor.core.get_editing_action_unit():
                return QtGui.QBrush(QtGui.QColor(152, 195, 121))
        elif role == QtCore.Qt.ForegroundRole:
            if index.data() == facseditor.core.get_editing_action_unit():
                return QtGui.QBrush(QtGui.QColor(43, 43, 43))
        else:
            return super(ActionUnitsModel, self).data(index, role)
