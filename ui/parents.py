import json
import logging
from collections import OrderedDict

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
import maya.cmds as cmds

from icarus.ui.settings import get_settings
from icarus.ui.signals import clear_all_signals, publish, subscribe
from icarus.vendor.Qt import QtWidgets, QtCore
import icarus.dag

logger = logging.getLogger(__name__)


class IcarusParentSpaces(MayaQWidgetBaseMixin, QtWidgets.QMainWindow):

    ui_name = 'icarus_parent_spaces'

    space_types = OrderedDict((
        ('Parent', 'parent'),
        ('Orient', 'orient'),
        ('Point', 'point'),
    ))

    def __init__(self, parent=None):
        super(IcarusParentSpaces, self).__init__(parent)

        self._nice_names = {}
        self._current_driver = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Icarus - Parent Spaces')

        self.content = QtWidgets.QWidget()

        self.child_content = QtWidgets.QWidget()
        self.child = QtWidgets.QLineEdit()
        self.pick_child_button = QtWidgets.QPushButton('Pick Selected')

        self.space_type = QtWidgets.QComboBox()

        self.parents_content = QtWidgets.QWidget()
        self.parents = QtWidgets.QListView()
        self.add_parent_button = QtWidgets.QPushButton('Add Selected')
        self.remove_parents_button = QtWidgets.QPushButton('Remove')

        self.nice_name = QtWidgets.QLineEdit()

        self.update_button = QtWidgets.QPushButton('Create')
        self.delete_button = QtWidgets.QPushButton('Delete All')

        self.setCentralWidget(self.content)

        layout = QtWidgets.QVBoxLayout()
        self.content.setLayout(layout)

        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        child_layout = QtWidgets.QHBoxLayout()
        self.child_content.setLayout(child_layout)
        child_layout.addWidget(self.child)
        child_layout.addWidget(self.pick_child_button)

        parents_layout = QtWidgets.QVBoxLayout()
        self.parents_content.setLayout(parents_layout)
        parents_layout.addWidget(self.parents)
        parents_actions_layout = QtWidgets.QHBoxLayout()
        parents_layout.addLayout(parents_actions_layout)
        parents_actions_layout.addWidget(self.add_parent_button)
        parents_actions_layout.addWidget(self.remove_parents_button)

        form.addRow('Child Control:', self.child_content)
        form.addRow('Space Type:', self.space_type)
        form.addRow('Parent Transforms:', self.parents_content)
        form.addRow('Nice Name:', self.nice_name)

        actions_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(actions_layout)

        actions_layout.addWidget(self.update_button)
        actions_layout.addWidget(self.delete_button)

        self.child.setEnabled(False)

        self.space_type.addItems(self.space_types.keys())
        self.space_type.setEnabled(False)

        self.parents.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.parents.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        self.nice_name.setEnabled(False)
        self.add_parent_button.setEnabled(False)
        self.remove_parents_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        child_layout.setContentsMargins(0, 0, 0, 0)
        parents_layout.setContentsMargins(0, 0, 0, 0)

        self.model = QtCore.QStringListModel()
        self.parents.setModel(self.model)

        self.pick_child_button.released.connect(self.pick_child)
        self.parents.selectionModel().currentChanged.connect(self._on_current_parent_changed)
        self.nice_name.textChanged.connect(self._on_nice_name_changed)
        self.add_parent_button.released.connect(self.add_parent)
        self.remove_parents_button.released.connect(self.remove_parents)
        self.update_button.released.connect(self.update)
        self.delete_button.released.connect(self.delete_all)

    def pick_child(self):
        """Pick the child from Maya's selection."""
        selection = cmds.ls(selection=True)
        if not selection:
            logger.warning('Please select an Icarus control to start.')
            return
        control = selection[-1]
        self.set_child(control)
        self.space_type.setEnabled(True)
        self.nice_name.setEnabled(True)
        self.add_parent_button.setEnabled(True)
        self.remove_parents_button.setEnabled(True)
        self.update_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def set_child(self, control):
        """Set ``control`` as the child for the parent space operation.

        This method will update the ``Child Control`` field if the GUI,
        and fill the parents list if the control already have parents set.

        :param control: Name of the control node to select.
        :type control: str
        """
        self.child.setText(control)
        self._current_driver = None
        self._nice_names = {}

        # If the control has a parent, orient or point space,
        # Then set the Space Type field and lock it.
        # Also load the current space drivers.
        space_type, drivers = self._control_configuration()
        if space_type and drivers:
            # Get the nice name of this space
            name = {v: k for k, v in self.space_types.iteritems()}[space_type]
            self.model.setStringList(drivers.values())
            self.space_type.setCurrentText(name)
        else:
            self.model.setStringList([])
            self.space_type.setCurrentText(self.space_types.keys()[0])

        self._update_ui_state()

    def add_parent(self):
        """Add a parent from Maya's selection."""
        if not self.child.text():
            logger.warning('Please pick a child control first.')
            return
        selection = cmds.ls(selection=True)
        if not selection:
            logger.warning('Please select parent transforms to start.')
            return

        parents = self.model.stringList()
        selection = [p for p in selection if p not in parents]
        self.model.setStringList(parents + selection)

    def remove_parents(self):
        """Remove parents selected in the GUI."""
        selection = self.parents.selectionModel().selectedRows()
        parents = self.model.stringList()
        remove = [
            self.model.data(index, QtCore.Qt.DisplayRole)
            for index in selection
        ]
        self.model.setStringList([p for p in parents if p not in remove])

    def update(self):
        """Update the parent space data of the selected control.

        This method will only update the parent space data contained in
        the control, users will have to manually unbuild and rebuild the
        rig in order for the parent spaces to be created.
        """
        ctl = self.child.text()
        if not ctl:
            logger.warning('Please pick a child control first.')
            return

        prev_space_type, prev_drivers = self._control_configuration()

        drivers = self.model.stringList()
        name = self.space_type.currentText()
        space_type = self.space_types[name]

        # Transform the list of drivers to a mapping of
        # nice name: transform name.
        _drivers = OrderedDict()
        for driver in drivers:
            _drivers[self._nice_names.get(driver, driver)] = driver
        drivers = _drivers

        space_changed = space_type != prev_space_type
        drivers_changed = drivers != prev_drivers.values()
        if prev_drivers and (space_changed or drivers_changed):
            icarus.dag.remove_parent_spaces(ctl)

        if drivers:
            icarus.dag.create_space_switching(ctl, drivers, space_type)

        data = json.dumps({
            space_type: drivers,
        })
        cmds.setAttr(ctl + '.parent_space_data', data, type='string')

        self._update_ui_state()

    def delete_all(self):
        """Deletes all parent spaces set on the selected control."""
        ctl = self.child.text()
        if not ctl:
            logger.warning('Please pick a child control first.')
            return

        button = QtWidgets.QMessageBox.warning(
            self,
            'Icarus - Delete Parent Spaces',
            'You are about to delete all parent spaces '
            'set on %s, continue ?' % ctl,
            QtWidgets.QMessageBox.Yes
            | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )
        if button != QtWidgets.QMessageBox.Yes:
            return

        icarus.dag.remove_parent_spaces(ctl)
        self.model.setStringList([])
        cmds.setAttr(ctl + '.parent_space_data', '{}', type='string')

        self._update_ui_state()

    def _update_ui_state(self):
        """Update some ui elements depending on the control and parents."""
        if self.model.stringList():
            self.update_button.setText('Update')
        else:
            self.update_button.setText('Create')

    def _control_configuration(self):
        """Return selected control current spaces data."""
        ctl = self.child.text()
        if not ctl:
            return None, {}

        data = cmds.getAttr(ctl + '.parent_space_data')
        spaces = json.loads(data, object_pairs_hook=OrderedDict)
        if not hasattr(spaces, 'get'):
            # Data is either corrupt or serialization method has changed.
            return

        for space_type in self.space_types.values():
            drivers = spaces.get(space_type, {})
            if drivers:
                return space_type, drivers

        return None, {}

    def _on_current_parent_changed(self, index):
        """Update the nice name field.

        :param index: New current index.
        :type index: PySide2.QtCore.QModelIndex
        """
        driver = self.model.data(index, QtCore.Qt.DisplayRole)
        self._current_driver = driver
        name = self._nice_names.get(driver, driver)
        self.nice_name.setText(name)

    def _on_nice_name_changed(self, name):
        """Update the internal nice name data.

        :param name: New name to set on the current parent.
        :type name: str
        """
        self._nice_names[self._current_driver] = name