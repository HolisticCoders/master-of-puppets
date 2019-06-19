def clear_layout(layout):
    item = layout.takeAt(0)
    while item:
        widget = item.widget()
        widget.setParent(None)
        widget.deleteLater()
        item = layout.takeAt(0)


def hsv_to_rgb(h, s, v):
    """Convert HSV values RGB.

        See https://stackoverflow.com/a/26856771.

        :param h: Hue component of the color to convert.
        :param s: Saturation component of the color to convert.
        :param v: Value component of the color to convert.
        :rtype: tuple
        """
    if s == 0.0:
        v *= 255
        return (v, v, v)
    i = int(h * 6.0)  # XXX assume int() truncates!
    f = (h * 6.0) - i
    p, q, t = (
        int(255 * (v * (1.0 - s))),
        int(255 * (v * (1.0 - s * f))),
        int(255 * (v * (1.0 - s * (1.0 - f)))),
    )
    v *= 255
    i %= 6
    if i == 0:
        return (v, t, p)
    if i == 1:
        return (q, v, p)
    if i == 2:
        return (p, v, t)
    if i == 3:
        return (p, q, v)
    if i == 4:
        return (t, p, v)
    if i == 5:
        return (v, p, q)
