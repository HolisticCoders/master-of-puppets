def clear_layout(layout):
    item = layout.takeAt(0)
    while item:
        widget = item.widget()
        widget.setParent(None)
        widget.deleteLater()
        item = layout.takeAt(0)