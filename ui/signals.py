"""Minimal observer/publisher implementation for all your GUI needs."""
import traceback
from collections import defaultdict

_SIGNALS = defaultdict(list)


def clear_all_signals():
    """Clear all signals.

    Calling this function will unsubscribe all functions.
    """
    _SIGNALS.clear()


def subscribe(name, func):
    """Subscribe ``func`` to a publisher.

    :param name: Signal to observe. When ``name`` is called
                 by :func:`publish`, ``func`` will be called.
    :param func: Function to register to the ``name`` signal.
    :type name: str
    :type func: callable
    """
    _SIGNALS[name].append(func)


def unsubscribe(name, func):
    """Unsubscribe ``func`` from a publisher.

    :param name: Signal to stop to observe.
    :param func: Function to disconnect from the ``name`` signal.
    :type name: str
    :type func: callable
    """
    while func in _SIGNALS[name]:
        _SIGNALS[name].remove(func)


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
    ret = {}
    for func in _SIGNALS[name]:
        try:
            res = func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            continue
        ret[func] = res
    return ret
