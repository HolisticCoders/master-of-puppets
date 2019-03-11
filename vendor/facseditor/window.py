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


def get_action_units_dict():
    facs_node = ensure_facs_node_exists()
    value = cmds.getAttr(facs_node + '.actionUnits')
    action_units = json.loads(value, object_pairs_hook=OrderedDict) if value else {}
    return action_units


def get_action_units():
    return get_action_units_dict().keys()


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
        self.action_units_list = QtWidgets.QListView()
        self.action_units_model = QtCore.QStringListModel()
        self.action_units_list.setModel(self.action_units_model)
        self.action_units_model.setStringList(get_action_units())
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

        ensure_facs_node_exists()

    def facs_selection_changed(self):
        self.update_controllers_model()

    def update_controllers_model(self):
        if not self.action_units_list.selectionModel().selectedIndexes():
            controllers = []
        else:
            current_action_unit = self.action_units_list.selectionModel().currentIndex().data()
            action_units_dict = get_action_units_dict()
            controllers = action_units_dict[current_action_unit]
        self.controllers_model.setStringList(controllers)

    def update_action_units_model(self):
        self.action_units_model.setStringList(get_action_units())

    def controllers_selection_changed(self):
        controllers_names = [c.data() for c in self.controllers_list.selectionModel().selectedIndexes()]
        cmds.select(controllers_names)

    def add_action_unit(self):
        facs_node = ensure_facs_node_exists()
        value = cmds.getAttr(facs_node + '.actionUnits')
        action_units = json.loads(value, object_pairs_hook=OrderedDict) if value else {}
        name = 'New Action Unit ' + str(len(action_units)).zfill(3)
        action_units[name] = []
        cmds.setAttr(facs_node + '.actionUnits', json.dumps(action_units), type='string')
        self.action_units_model.setStringList(get_action_units())

    def remove_action_units(self):
        facs_node = ensure_facs_node_exists()
        value = cmds.getAttr(facs_node + '.actionUnits')
        action_units = json.loads(value, object_pairs_hook=OrderedDict) if value else {}

        selected_units_indices = self.action_units_list.selectionModel().selectedIndexes()
        for index in selected_units_indices:
            action_unit = index.data()
            if action_unit in action_units.keys():
                del action_units[action_unit]
        cmds.setAttr(facs_node + '.actionUnits', json.dumps(action_units), type='string')
        self.update_action_units_model()

    def rename_action_unit(self, new_key, new_index):
        action_units_dict = get_action_units_dict()
        new_dict = OrderedDict()
        if new_key in action_units_dict.keys():
            if action_units_dict.keys().index(new_key) != new_index:
                # log only if the name is not the one we're currently editing
                logger.warning('An action unit named "{}" already exists'.format(
                    new_key
                ))
            new_dict = action_units_dict
        else:
            key_to_change = action_units_dict.keys()[new_index]
            for key, value in action_units_dict.iteritems():
                if key == key_to_change:
                    new_dict[new_key] = value
                else:
                    new_dict[key] = value
        return new_dict

    def move_action_unit(self, new_key, new_index):
        action_units_dict = get_action_units_dict()
        action_units_dict[new_key] = action_units_dict.pop(new_key)
        i = 0
        for key, value in action_units_dict.items():
            if key != new_key and i >= new_index:
                action_units_dict[key] = action_units_dict.pop(key)
            i += 1
        return action_units_dict

    def action_units_data_changed(self, topLeft, bottomRight, roles):
        new_index = topLeft.row()
        new_key = topLeft.data()

        if roles[0] == QtCore.Qt.DisplayRole:
            new_dict = self.move_action_unit(new_key, new_index)

        elif roles[0] == QtCore.Qt.EditRole:
            new_dict = self.rename_action_unit(new_key, new_index)
        facs_node = ensure_facs_node_exists()
        cmds.setAttr(
            facs_node + '.actionUnits',
            json.dumps(new_dict),
            type='string'
        )
        self.update_action_units_model()


    def edit_action_unit(self):
        print "Editing Action unit"

    def finish_edit_action_unit(self):
        print "Finishing Editing Action unit"

    def add_controllers_to_action_unit(self):
        if not self.action_units_list.selectionModel().selectedIndexes():
            return
        last_action_unit = self.action_units_list.selectionModel().currentIndex().data()
        maya_sel = cmds.ls(sl=True)
        action_units_dict = get_action_units_dict()
        new_controls = set(action_units_dict.get(last_action_unit, [])) | set(maya_sel)
        action_units_dict[last_action_unit] = list(sorted(new_controls))
        facs_node = ensure_facs_node_exists()
        cmds.setAttr(
            facs_node + '.actionUnits',
            json.dumps(action_units_dict),
            type='string'
        )
        self.update_controllers_model()

    def remove_controllers_from_action_unit(self):
        last_action_unit = self.action_units_list.selectionModel().currentIndex().data()
        selected_controllers = [c.data() for c in self.controllers_list.selectionModel().selectedIndexes()]
        action_units_dict = get_action_units_dict()
        controllers = action_units_dict[last_action_unit]
        new_controllers = [c for c in controllers if c not in selected_controllers]
        action_units_dict[last_action_unit] = new_controllers
        facs_node = ensure_facs_node_exists()
        cmds.setAttr(
            facs_node + '.actionUnits',
            json.dumps(action_units_dict),
            type='string'
        )
        self.update_controllers_model()


# class ActionUnitsModel(QtCore.QAbstractListModel):
#     def __init__(self, parent=None):
#         super(ActionUnitsModel, self).__init__(parent)

#     @property
#     def action_units(self):
#         facs_node = ensure_facs_node_exists()
#         value = cmds.getAttr(facs_node + '.actionUnits')
#         action_units = json.loads(value, object_pairs_hook=OrderedDict).keys() if value else {}
#         return action_units

#     def rowCount(self, parent):
#         return len(self.action_units)

#     def data(self, index, role):
#         if role == QtCore.Qt.DisplayRole:
#             row = index.row()
#             return self.action_units[row]
#         if role == QtCore.Qt.EditRole:
#             row = index.row()
#             return self.action_units[row]

#     def setData(self, index, value, role):
#         if not value:
#             logger.warning('You must enter a name for the action unit.')
#             return False

#         facs_node = ensure_facs_node_exists()
#         action_units = cmds.getAttr(facs_node + '.actionUnits')
#         action_units = json.loads(action_units, object_pairs_hook=OrderedDict) if value else {}
#         row = index.row()
#         if value in action_units.keys():
#             if action_units.keys().index(value) != row:
#                 # log only if the name is not the one we're currently editing
#                 logger.warning('An action unit named "{}" already exists'.format(
#                     value
#                 ))
#             return False

#         old_key = action_units.keys()[row]
#         action_units[value] = action_units.pop(old_key)
#         cmds.setAttr(
#             facs_node + '.actionUnits',
#             json.dumps(action_units),
#             type='string'
#         )
#         return True

#     def flags(self, index):
#         default_flags = super(ActionUnitsModel, self).flags(index)
#         return (QtCore.Qt.ItemIsEditable | default_flags)
