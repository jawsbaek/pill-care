"""Langfuse `@observe` re-export with a graceful no-op fallback.

If `langfuse` is not installed or fails to import at module load time,
we expose a decorator that preserves the wrapped function's signature so
the rest of the codebase can decorate nodes unconditionally.
"""

from __future__ import annotations

from typing import Any, Callable

try:
    from langfuse import observe as _observe  # type: ignore[import-not-found]
except Exception:  # pragma: no cover — import error or missing extras

    def _observe(*dargs: Any, **dkwargs: Any) -> Callable[..., Any]:
        # Support both `@observe` and `@observe(name=...)` forms
        if dargs and callable(dargs[0]) and not dkwargs:
            return dargs[0]

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            return fn

        return decorator


observe = _observe

__all__ = ["observe"]
