from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, Mapping, Optional, TypeVar

TFieldValues = TypeVar("TFieldValues", bound=Mapping[str, Any])


@dataclass(frozen=True)
class FormState:
    is_submitting: bool = False
    is_valid: bool = True


@dataclass(frozen=True)
class UseFormReturn(Generic[TFieldValues]):
    # Mirrors the ergonomic shape of react-hook-form but is intentionally incomplete for now.
    form_state: FormState

    def handle_submit(self, on_valid: Callable[[TFieldValues], object]) -> Callable[[], object]:
        raise NotImplementedError(
            "ryact-hook-form is a scaffold; handle_submit is not implemented."
        )


def use_form(
    *, default_values: Optional[Mapping[str, Any]] = None
) -> UseFormReturn[Mapping[str, Any]]:
    raise NotImplementedError("ryact-hook-form is a scaffold; use_form is not implemented.")


__all__ = ["FormState", "UseFormReturn", "use_form"]

