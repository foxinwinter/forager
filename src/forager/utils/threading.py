"""Threading helpers for cancellable background work.

The GUI keeps all network/disk work off the UI thread (see
``forager.ui.workers``). A :class:`StopFlag` is the standard cooperative
cancellation mechanism passed to those workers.
"""
from __future__ import annotations

import threading


class StopFlag(threading.Event):
    """A :class:`threading.Event` used purely as a cancellation flag.

    Workers poll :meth:`is_set` in their loops and exit early; callers set
    it to request cancellation. Unlike a raw ``Event`` the name documents
    intent and gives workers a single place to observe state.
    """
