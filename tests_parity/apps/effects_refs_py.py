from __future__ import annotations

from collections.abc import Callable

from ryact import create_element, create_ref, h, use_effect, use_ref, use_state


def make_effects_refs_app(*, sink: dict[str, object], log: list[str]) -> Callable[[], object]:
    def App() -> object:
        on, set_on = use_state(True)
        sink["set_on"] = set_on

        obj_ref = create_ref()
        sink["obj_ref"] = obj_ref

        def cb_ref(value: object | None) -> None:
            log.append(f"cb_ref:{'set' if value is not None else 'clear'}")

        def Child() -> object:
            def effect() -> Callable[[], None]:
                log.append("effect:mount")

                def cleanup() -> None:
                    log.append("effect:unmount")

                return cleanup

            use_effect(effect)
            # Also track per-render via use_ref
            r = use_ref("x")
            _ = r  # keep
            return h("div", {"ref": cb_ref}, "child")

        if on:
            return h(
                "section", None, h("div", {"ref": obj_ref}, "host"), create_element(Child, None)
            )
        return h("section", None, "off")

    return App


def build_tree(*, sink: dict[str, object], log: list[str]) -> object:
    App = make_effects_refs_app(sink=sink, log=log)
    return create_element(App, None)
