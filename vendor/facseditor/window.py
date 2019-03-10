import logging
import json
from collections import OrderedDict

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.cmds as cmds

from icarus.vendor.Qt import QtWidgets, QtCore

logger = logging.getLogger(__name__)


def ensure_facs_node_exists():
    node = 'FACS_CONTROL'
    if not cmds.objExists('FACS_CONTROL'):
        cmds.createNode('transform', name=node)
        cmds.addAttr(node, ln='actionUnits', dataType='string')
    return node


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

        main_layout = QtWidgets.QHBoxLayout()
        central_widget.setLayout(main_layout)

        # FACS action units part
        facs_group = QtWidgets.QGroupBox('FACS Action units')
        main_layout.addWidget(facs_group)

        facs_layout = QtWidgets.QVBoxLayout()
        facs_group.setLayout(facs_layout)
        self.facs_list = QtWidgets.QListView()
        self.action_units_model = ActionUnitsModel()
        self.facs_list.setModel(self.action_units_model)
        self.facs_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        facs_layout.addWidget(self.facs_list)
        facs_actions_layout = QtWidgets.QHBoxLayout()
        facs_layout.addLayout(facs_actions_layout)

        facs_add_button = QtWidgets.QPushButton('Add')
        facs_add_button.released.connect(self.add_action_unit)
        facs_actions_layout.addWidget(facs_add_button)
        facs_remove_button = QtWidgets.QPushButton('Remove')
        facs_remove_button.released.connect(self.remove_action_units)
        facs_actions_layout.addWidget(facs_remove_button)
        facs_edit_button = QtWidgets.QPushButton('Edit')
        facs_edit_button.released.connect(self.edit_action_unit)
        facs_actions_layout.addWidget(facs_edit_button)
        facs_finish_edit_button = QtWidgets.QPushButton('Finish Edit')
        facs_finish_edit_button.released.connect(self.finish_edit_action_unit)
        facs_actions_layout.addWidget(facs_finish_edit_button)


        # Controllers part
        controllers_group = QtWidgets.QGroupBox('Controllers')
        main_layout.addWidget(controllers_group)

        controllers_layout = QtWidgets.QVBoxLayout()
        controllers_group.setLayout(controllers_layout)
        controllers_list = QtWidgets.QListView()
        controllers_layout.addWidget(controllers_list)
        controllers_actions_layout = QtWidgets.QHBoxLayout()
        controllers_layout.addLayout(controllers_actions_layout)

        controllers_add_button = QtWidgets.QPushButton('Add Selected')
        controllers_add_button.released.connect(self.add_controllers_to_action_unit)
        controllers_actions_layout.addWidget(controllers_add_button)
        controllers_remove_button = QtWidgets.QPushButton('Remove')
        controllers_remove_button.released.connect(self.remove_controllers_from_action_unit)
        controllers_actions_layout.addWidget(controllers_remove_button)

        ensure_facs_node_exists()

    def add_action_unit(self):
        facs_node = ensure_facs_node_exists()
        value = cmds.getAttr(facs_node + '.actionUnits')
        action_units = json.loads(value, object_pairs_hook=OrderedDict) if value else {}
        name = 'New Action Unit ' + str(len(action_units)).zfill(3)
        action_units[name] = []
        cmds.setAttr(facs_node + '.actionUnits', json.dumps(action_units), type='string')
        index = action_units.keys().index(name)
        self.action_units_model.dataChanged.emit(index, 0, [QtCore.Qt.DisplayRole])

    def remove_action_units(self):
        facs_node = ensure_facs_node_exists()
        value = cmds.getAttr(facs_node + '.actionUnits')
        action_units = json.loads(value, object_pairs_hook=OrderedDict) if value else {}

        selected_units_indices = self.facs_list.selectionModel().selectedIndexes()
        for index in selected_units_indices:
            action_unit = index.data()
            if action_unit in action_units.keys():
                del action_units[action_unit]
        cmds.setAttr(facs_node + '.actionUnits', json.dumps(action_units), type='string')
        self.action_units_model.dataChanged.emit(0, 0, [QtCore.Qt.DisplayRole])

    def edit_action_unit(self):
        print "Editing Action unit"

    def finish_edit_action_unit(self):
        print "Finishing Editing Action unit"

    def add_controllers_to_action_unit(self):
        print "Adding Controller"

    def remove_controllers_from_action_unit(self):
        print "Removing Controller"


class ActionUnitsModel(QtCore.QAbstractListModel):
    def __init__(self, parent=None):
        super(ActionUnitsModel, self).__init__(parent)

    @property
    def action_units(self):
        facs_node = ensure_facs_node_exists()
        value = cmds.getAttr(facs_node + '.actionUnits')
        action_units = json.loads(value, object_pairs_hook=OrderedDict).keys() if value else {}
        return action_units

    def rowCount(self, parent):
        return len(self.action_units)

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            return self.action_units[row]
        if role == QtCore.Qt.EditRole:
            row = index.row()
            return self.action_units[row]

    def setData(self, index, value, role):
        if not value:
            logger.warning('You must enter a name for the action unit.'.format(
                value
            ))
            return False

        facs_node = ensure_facs_node_exists()
        action_units = cmds.getAttr(facs_node + '.actionUnits')
        action_units = json.loads(action_units, object_pairs_hook=OrderedDict) if value else {}
        row = index.row()
        if value in action_units.keys():
            if action_units.keys().index(value) != row:
                # log only if the name is not the one we're currently editing
                logger.warning('An action unit named "{}" already exists'.format(
                    value
                ))
            return False

        old_key = action_units.keys()[row]
        action_units[value] = action_units.pop(old_key)
        cmds.setAttr(
            facs_node + '.actionUnits',
            json.dumps(action_units),
            type='string'
        )
        return True

    def flags(self, index):
        default_flags = super(ActionUnitsModel, self).flags(index)
        return (QtCore.Qt.ItemIsEditable | default_flags)
