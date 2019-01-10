from collections import defaultdict

_SIGNALS = defaultdict(list)


def observe(name, func):
    _SIGNALS[name].append(func)


def publish(name, *args, **kwargs):
    for func in _SIGNALS[name]:
        func(*args, **kwargs)
