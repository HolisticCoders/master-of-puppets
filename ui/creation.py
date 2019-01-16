from functools import partial

from icarus.core.rig import Rig
from icarus.modules import all_rig_modules
from icarus.ui.signals import publish
from icarus.utils.case import title
from icarus.vendor.Qt import QtCore, QtWidgets


class CreationPanel(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super(CreationPanel, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setObjectName('icarus_creation_panel')
        self.setWindowTitle('Creation Panel')

        self.setWidget(QtWidgets.QWidget())

        self.layout = QtWidgets.QVBoxLayout()
        self.widget().setLayout(self.layout)

        self.scroll = QtWidgets.QScrollArea()
        self.layout.addWidget(self.scroll)

        self.scroll.setWidgetResizable(True)

        self.content = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout()

        self.content.setLayout(self.content_layout)

        for module in all_rig_modules:
            button = QtWidgets.QPushButton(title(module))
            button.released.connect(partial(self._create_module, module))
            self.content_layout.addWidget(button)

        self.content_layout.addStretch()

        self.scroll.setWidget(self.content)

    def _create_module(self, module_type):
        rig = Rig()
        module = rig.add_module(
            module_type,
            name=module_type.lower(),
            parent_joint='root_M_000_deform'
        )

        publish('module-created', module)
