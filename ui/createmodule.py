from icarus.modules import all_rig_modules
from icarus.ui.signals import publish
from icarus.vendor.Qt import QtWidgets
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from icarus.core.rig import Rig

class CreateModulePanel(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(CreateModulePanel, self).__init__(parent)
        self.setWindowTitle('Icarus Create Module')

        self.layout= QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.modules_widget = QtWidgets.QListWidget()
        self.layout.addWidget(self.modules_widget)
        for module in all_rig_modules:
            item = QtWidgets.QListWidgetItem(module)
            self.modules_widget.addItem(item)

        self.create_button = QtWidgets.QPushButton('Create')
        self.layout.addWidget(self.create_button)
        self.create_button.released.connect(self._create_module)

    def _create_module(self):
        sel = self.modules_widget.selectedItems()
        if sel:
            module_type = sel[0].text()
            rig = Rig()
            rig.add_module(
                module_type,
                name=module_type.lower(),
                parent_joint='root_M_000_deform'
            )

            publish('module-created')

