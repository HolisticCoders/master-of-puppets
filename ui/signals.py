"""Minimal observer/publisher implementation for all your GUI needs."""
from collections import defaultdict
from weakref import WeakKeyDictionary

_SIGNALS = defaultdict(list)


def observe(name, func):
    """Subscribe ``func`` to a publisher.

    :param name: Signal to observe. When ``name`` is called
                 by :func:`publish`, ``func`` will be called.
    :param func: Function to register to the ``name`` signal.
    :type name: str
    :type func: callable
    """
    _SIGNALS[name].append(func)


def publish(name, *args, **kwargs):
    """Emits a signal to all observers subscribed.

    You can use ``args`` and ``kwargs`` to call subscribers
    with these arguments.

    Observers return values are collected and returned in a
    :class:`weakref.WeakKeyDictionary` keyed by observer.

    :param name: Name of the signal to emit.
                 Observers subscribed to the same
                 ``name`` will be notified.
    :type name: str
    :rtype: weakref.WeakKeyDictionary
    """
    ret = WeakKeyDictionary()
    for func in _SIGNALS[name]:
        res = func(*args, **kwargs)
        ret[func] = res
    return ret
