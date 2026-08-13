"""Tool registry.

Each tool declares its schema once via the `register` decorator. The schema is
reused to build Gemini function declarations, so adding a tool means writing one
function and nothing else.
"""
import logging
from dataclasses import dataclass
from typing import Callable

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., dict]


_REGISTRY: dict[str, ToolSpec] = {}


def register(name: str, description: str, parameters: dict):
    def decorator(handler: Callable[..., dict]) -> Callable[..., dict]:
        if name in _REGISTRY:
            raise ValueError(f"Tool '{name}' is already registered")
        _REGISTRY[name] = ToolSpec(name, description, parameters, handler)
        return handler

    return decorator


def function_declarations() -> list[dict]:
    return [
        {"name": spec.name, "description": spec.description, "parameters": spec.parameters}
        for spec in _REGISTRY.values()
    ]


def run(name: str, chat_id: int, arguments: dict) -> dict:
    """Run a tool and always return a dict the model can read.

    Errors are returned rather than raised so the model can apologise or retry
    with different arguments instead of the whole request failing.
    """
    spec = _REGISTRY.get(name)
    if spec is None:
        return {"error": f"Unknown tool '{name}'"}
    try:
        return spec.handler(chat_id=chat_id, **(arguments or {}))
    except (ValueError, TypeError) as exc:
        log.info("Tool %s rejected arguments: %s", name, exc)
        return {"error": str(exc)}
    except Exception as exc:  # surfaced to the model, logged for us
        log.exception("Tool %s failed", name)
        return {"error": f"{name} failed: {exc}"}


# Import for side effects: each module registers its tools on import.
from . import calendar_tools, messaging, notes  # noqa: E402,F401
