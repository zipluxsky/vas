# project/app/core/cli.py
from __future__ import annotations

import asyncio
import inspect
import json
import threading
import types
import typing as t
from pathlib import Path

import click
from pydantic import BaseModel

cli = click.Group(help="Project command-line interface")
_groups: dict[str, click.Group] = {}


def _get_group(name: str | None) -> click.Group:
    if not name:
        return cli
    if name not in _groups:
        _groups[name] = click.Group(name=name, help=f"{name} commands")
        cli.add_command(_groups[name], name)
    return _groups[name]


# --------- FIX 1: Type unwrapping (Optional[list[str]] etc.) ----------
NoneType = type(None)


def _unwrap_optional(tp: t.Any) -> t.Any:
    """If tp is Optional[T] / Union[T, None], return T. else tp."""
    origin = t.get_origin(tp)
    args = t.get_args(tp)
    # Handle both typing.Union and PEP604 unions (X | None)
    union_origins = {t.Union}
    if hasattr(types, "UnionType"):
        union_origins.add(types.UnionType)  # Python 3.10+

    if origin in union_origins and args:
        non_none = [a for a in args if a is not NoneType]
        if len(non_none) == 1:
            return non_none[0]

    return tp


def _is_list_type(tp: t.Any) -> bool:
    tp = _unwrap_optional(tp)
    origin = t.get_origin(tp)
    return origin in (list, t.List)


def _pytype_to_click(tp: t.Any) -> t.Any:
    tp = _unwrap_optional(tp)
    origin = t.get_origin(tp)

    if origin in (list, t.List):
        return str  # list items treated as strings

    if tp in (str, int, float, bool):
        return tp

    return str


def _flatten_comma_multiple(values: tuple[str, ...] | None) -> list[str] | None:
    if not values:
        return None
    out: list[str] = []
    for v in values:
        out.extend([x.strip() for x in v.split(",") if x.strip()])
    return out or None


#
# FIX 2: Run coroutine even if event loop is already running
#
def _run_coroutine_sync(coro: t.Awaitable[t.Any]) -> t.Any:
    """
    Run coroutine from sync code.
    - If no running loop: asyncio.run(coro)
    - If already in a running loop (pytest-asyncio/Jupyter): run in a new thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_box: dict[str, t.Any] = {}
    error_box: dict[str, BaseException] = {}

    def _thread_target():
        try:
            result_box["result"] = asyncio.run(coro)
        except BaseException as e:
            error_box["error"] = e

    th = threading.Thread(target=_thread_target, daemon=True)
    th.start()
    th.join()

    if "error" in error_box:
        raise error_box["error"]
    return result_box.get("result")


def expose_cli(
    *,
    name: str,
    model: type[BaseModel],
    runner: t.Callable[[BaseModel], t.Awaitable[t.Any] | t.Any],
    group: str | None = None,
    help: str | None = None,
) -> None:
    grp = _get_group(group)
    params: list[click.Parameter] = []

    # Pydantic v2: model.model_fields; v1 fallback: model.__fields__
    try:
        fields = model.model_fields  # type: ignore[attr-defined]
    except AttributeError:
        fields = model.__fields__  # type: ignore[attr-defined]

    field_defs: dict[str, t.Any] = {}
    for fname, f in fields.items():
        try:
            annotation = f.annotation  # v2
        except Exception:
            annotation = getattr(f, "outer_type_", str)  # v1 fallback
        field_defs[fname] = annotation

    for fname, annotation in field_defs.items():
        opt_name = f"--{fname.replace('_', '-')}"
        click_type = _pytype_to_click(annotation)

        if _is_list_type(annotation):
            # IMPORTANT: multiple=True implies Click returns a tuple
            # Use default=() instead of None for multiple options
            params.append(
                click.Option(
                    param_decls=[opt_name],
                    multiple=True,
                    type=str,
                    default=(),
                    help=f"{fname} (repeat flag or comma-separated)",
                    callback=lambda ctx, param, value: _flatten_comma_multiple(value),
                )
            )
        else:
            params.append(
                click.Option(
                    param_decls=[opt_name],
                    type=click_type,
                    default=None,
                    help=f"{fname}",
                )
            )

    if "html_body" in field_defs:
        params.append(
            click.Option(
                param_decls=["--html-file"],
                type=click.Path(path_type=Path, exists=True, dir_okay=False, readable=True),
                default=None,
                help="Path to an HTML file to populate html_body",
            )
        )

    params.append(
        click.Option(
            param_decls=["--json"],
            type=click.Path(path_type=Path, exists=True, dir_okay=False, readable=True),
            default=None,
            help="Path to JSON file providing the request body",
        )
    )

    def _callback(**kwargs):
        json_path: Path | None = kwargs.pop("json", None)
        if json_path:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise click.ClickException("--json must contain an object")
        else:
            data = {}

        # Load html from file if provided
        html_file = kwargs.pop("html_file", None)
        if html_file is not None:
            data["html_body"] = Path(html_file).read_text(encoding="utf-8")

        # Overlay CLI args (ignore None)
        for k, v in kwargs.items():
            if v is not None:
                data[k] = v

        try:
            body = model(**data)
        except Exception as e:
            raise click.ClickException(f"Invalid arguments for {model.__name__}: {e}") from e

        res = runner(body)
        if inspect.iscoroutine(res):
            res = _run_coroutine_sync(t.cast(t.Awaitable[t.Any], res))
        if res is not None:
            click.echo(res)
        return res

    cmd = click.Command(
        name=name,
        params=params,
        callback=_callback,
        help=help or f"{name} (auto-generated from {model.__name__})",
    )
    grp.add_command(cmd)


# Backward compatibility: entry point may be referenced as "commands"
commands = cli

