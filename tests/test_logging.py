"""Library logging stays configurable and does not repeat caller-visible failures."""

from __future__ import annotations

import asyncio
import io
import logging

import pytest

from deepseek_cordis import Context, Fiber, FiberState


def _errors(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.levelno >= logging.ERROR]


def test_package_logger_has_null_handler_and_stays_quiet_without_configuration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = logging.getLogger("deepseek_cordis")
    assert any(isinstance(handler, logging.NullHandler) for handler in package.handlers)
    root = logging.getLogger()
    saved = root.handlers[:]
    root.handlers.clear()
    try:
        logging.getLogger("deepseek_cordis.fiber").error("contained")
        captured = capsys.readouterr()
    finally:
        root.handlers[:] = saved
    assert captured.out == ""
    assert captured.err == ""


def test_application_handler_receives_each_child_record_once() -> None:
    package = logging.getLogger("deepseek_cordis")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    level = package.level
    package.addHandler(handler)
    package.setLevel(logging.ERROR)
    try:
        logging.getLogger("deepseek_cordis.effects").error("routed")
    finally:
        package.removeHandler(handler)
        package.setLevel(level)
    assert stream.getvalue().count("routed") == 1


@pytest.mark.asyncio
async def test_unawaited_effect_failure_is_logged_once_with_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="deepseek_cordis")

    async def setup() -> None:
        raise ValueError("dropped")

    ctx = Context()
    ctx.effect(setup, "worker")
    background = asyncio.all_tasks() - {asyncio.current_task()}
    await asyncio.wait(background)
    records = _errors(caplog)
    assert len(records) == 1
    assert records[0].name == "deepseek_cordis.effects"
    assert records[0].getMessage() == "Effect worker async work failed"
    assert records[0].exc_info is not None
    assert isinstance(records[0].exc_info[1], ValueError)
    assert records[0].exc_info[1].args == ("dropped",)
    await ctx.fiber.dispose()
    assert _errors(caplog) == records


@pytest.mark.asyncio
async def test_fiber_setup_failure_is_logged_once_with_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="deepseek_cordis")
    failure = ValueError("setup failed")

    def setup(ctx: Context, config: object) -> None:
        raise failure

    root = Context()
    fiber = Fiber(root, setup)
    with pytest.raises(ValueError, match="setup failed"):
        await fiber
    records = _errors(caplog)
    assert len(records) == 1
    assert records[0].name == "deepseek_cordis.fiber"
    assert records[0].getMessage() == "Fiber root setup failed"
    assert records[0].exc_info is not None
    assert records[0].exc_info[1] is failure
    assert fiber.error is failure
    await root.fiber.dispose()


@pytest.mark.asyncio
async def test_fiber_cleanup_failure_is_logged_once_with_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="deepseek_cordis")
    failure = ValueError("cleanup")

    def setup(ctx: Context, config: object) -> object:
        def cleanup() -> None:
            raise failure

        return cleanup

    root = Context()
    fiber = await Fiber(root, setup)
    await fiber.dispose()
    records = _errors(caplog)
    assert len(records) == 1
    assert records[0].name == "deepseek_cordis.fiber"
    assert "cleanup failed" in records[0].getMessage()
    assert records[0].exc_info is not None
    assert records[0].exc_info[1] is failure
    assert fiber.cleanup_errors == (failure,)
    await root.fiber.dispose()


@pytest.mark.asyncio
async def test_service_check_failure_is_logged_once_with_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR, logger="deepseek_cordis")

    def check() -> bool:
        raise ValueError("not ready")

    root = Context()
    root.provide("database", object(), check=check)
    fiber = await root.inject(["database"], lambda ctx, cfg: None)
    records = _errors(caplog)
    assert len(records) == 1
    assert records[0].name == "deepseek_cordis.services"
    assert records[0].getMessage() == "Service database availability check failed"
    assert records[0].exc_info is not None
    assert isinstance(records[0].exc_info[1], ValueError)
    assert fiber.state is FiberState.PENDING
    await root.fiber.dispose()
