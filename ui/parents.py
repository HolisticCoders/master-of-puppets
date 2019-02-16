import json
import logging

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin
import maya.cmds as cmds

from icarus.ui.settings import get_settings
from icarus.ui.signals import clear_all_signals, publish, subscribe
from icarus.vendor.Qt import QtWidgets, QtCore

logger = logging.getLogger(__name__)


class IcarusParentSpaces(MayaQWidgetBaseMixin, QtWidgets.QMainWindow):

    ui_name = 'icarus_parent_spaces'

    def __init__(self, parent=None):
        super(IcarusParentSpaces, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('Icarus - Parent Spaces')

        self.content = QtWidgets.QWidget()

        self.child_content = QtWidgets.QWidget()
        self.child = QtWidgets.QLineEdit()
        self.pick_child_button = QtWidgets.QPushButton('Pick Selected')

        self.parents_content = QtWidgets.QWidget()
        self.parents = QtWidgets.QListView()
        self.add_parent_button = QtWidgets.QPushButton('Add Selected')
        self.remove_parents_button = QtWidgets.QPushButton('Remove')

        self.update_button = QtWidgets.QPushButton('Update')

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
        form.addRow('Parent Transforms:', self.parents_content)

        actions_layout = QtWidgets.QHBoxLayout()
        layout.addLayout(actions_layout)

        actions_layout.addWidget(self.update_button)

        self.child.setEnabled(False)
        self.parents.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.add_parent_button.setEnabled(False)
        self.remove_parents_button.setEnabled(False)
        self.update_button.setEnabled(False)

        child_layout.setContentsMargins(0, 0, 0, 0)
        parents_layout.setContentsMargins(0, 0, 0, 0)

        self.model = QtCore.QStringListModel()
        self.parents.setModel(self.model)

        self.pick_child_button.released.connect(self.pick_child)
        self.add_parent_button.released.connect(self.add_parent)
        self.remove_parents_button.released.connect(self.remove_parents)
        self.update_button.released.connect(self.update)

    def pick_child(self):
        """Pick the child from Maya's selection."""
        selection = cmds.ls(selection=True)
        if not selection:
            logger.warning('Please select an Icarus control to start.')
            return
        control = selection[-1]
        self.set_child(control)
        self.add_parent_button.setEnabled(True)
        self.remove_parents_button.setEnabled(True)
        self.update_button.setEnabled(True)

    def set_child(self, control):
        """Set ``control`` as the child for the parent space operation.

        This method will update the ``Child Control`` field if the GUI,
        and fill the parents list if the control already have parents set.

        :param control: Name of the control node to select.
        """
        self.child.setText(control)

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
        data = json.dumps(self.model.stringList())
        cmds.setAttr(ctl + '.parent_space_data', data, type='string')
