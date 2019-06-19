"""Qt widgets for mop fields."""
import maya.cmds as cmds

from mop.vendor.Qt import QtWidgets


class SpinBox(QtWidgets.QSpinBox):
    def __init__(self, field, *args, **kwargs):
        super(SpinBox, self).__init__(*args, **kwargs)
        self.field = field
        minValue = field.min_value
        maxValue = field.max_value
        if minValue is not None:
            self.setMinimum(minValue)
        else:
            self.setMinimum(-1000000)
        if maxValue is not None:
            self.setMaximum(maxValue)
        else:
            self.setMaximum(1000000)

    def get(self):
        return self.value()

    def set(self, value):
        self.setValue(value)

    def signal(self):
        return self.valueChanged


class LineEdit(QtWidgets.QLineEdit):
    def __init__(self, field, *args, **kwargs):
        super(LineEdit, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setText(value)

    def get(self):
        return self.text()

    def signal(self):
        return self.textChanged


class CheckBox(QtWidgets.QCheckBox):
    def __init__(self, field, *args, **kwargs):
        super(CheckBox, self).__init__(*args, **kwargs)
        self.field = field

    def set(self, value):
        self.setChecked(value)

    def get(self):
        return self.isChecked()

    def signal(self):
        return self.stateChanged


class ComboBox(QtWidgets.QComboBox):
    def __init__(self, field, *args, **kwargs):
        super(ComboBox, self).__init__(*args, **kwargs)
        self.field = field
        self.addItems(field.choices)

    def set(self, value):
        self.setCurrentText(value)

    def get(self):
        return self.currentText()

    def signal(self):
        return self.currentTextChanged


class ObjectPicker(QtWidgets.QWidget):
    def __init__(self, field, *args, **kwargs):
        super(ObjectPicker, self).__init__(*args, **kwargs)
        self.field = field

        self.setLayout(QtWidgets.QHBoxLayout())
        self._name = QtWidgets.QLineEdit()
        self._picker = QtWidgets.QPushButton("<<")
        self.layout().addWidget(self._name)
        self.layout().addWidget(self._picker)

        self._picker.released.connect(self._on_pick_pressed)

    def _on_pick_pressed(self):
        selection = cmds.ls(selection=True)
        if not selection:
            return
        self._name.setText(selection[-1])

    def set(self, value):
        self._name.setText(value)

    def get(self):
        return self._name.text()

    def signal(self):
        return self._name.textChanged


map_field_to_widget = {
    "BoolField": CheckBox,
    "IntField": SpinBox,
    "StringField": LineEdit,
    "ObjectField": ObjectPicker,
    "EnumField": ComboBox,
}
