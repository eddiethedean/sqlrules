from __future__ import annotations

import threading
from typing import Any

from sqlrules.ir import ModelIR


class ModelIRCache:
    """Thread-safe in-process cache of Phase-1 ModelIR keyed by model class.

    Cached values are immutable and may be shared across threads. Column
    objects are never stored here.

    Entries are held with **strong** references for the process lifetime
    (``ModelIR`` retains the model class, so a ``WeakKeyDictionary`` would
    not evict). Call :meth:`clear` to drop cached IR, especially when
    creating many ephemeral models (e.g. ``pydantic.create_model``).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._store: dict[type[Any], ModelIR] = {}

    def get(self, model: type[Any]) -> ModelIR | None:
        with self._lock:
            return self._store.get(model)

    def put(self, model: type[Any], model_ir: ModelIR) -> ModelIR:
        with self._lock:
            self._store[model] = model_ir
            return model_ir

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# Shared default cache for Compiler instances with cache=True.
_default_cache = ModelIRCache()


def default_cache() -> ModelIRCache:
    return _default_cache
