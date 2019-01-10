from collections import defaultdict
from weakref import WeakKeyDictionary

_SIGNALS = defaultdict(list)


def observe(name, func):
    _SIGNALS[name].append(func)


def publish(name, *args, **kwargs):
    ret = WeakKeyDictionary()
    for func in _SIGNALS[name]:
        res = func(*args, **kwargs)
        ret[func] = res
    return ret
