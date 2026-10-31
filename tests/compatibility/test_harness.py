"""Pinned Harness lifecycle regressions; publication-hook portions stay deferred."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Generator

import pytest

from deepseek_cordis import Context, Fiber, FiberState

pytestmark = [pytest.mark.asyncio, pytest.mark.compatibility]


async def test_reentrant_restart_joins_effect_setup_and_returned_cleanup() -> None:
    root = Context()
    entered = asyncio.Event()
    setup_release = asyncio.Event()
    cleanup_entered = asyncio.Event()
    cleanup_release = asyncio.Event()
    finished: list[str] = []

    async def setup() -> object:
        root.fiber.restart()
        entered.set()
        await setup_release.wait()
        finished.append("setup")

        async def cleanup() -> None:
            cleanup_entered.set()
            await cleanup_release.wait()
            finished.append("cleanup")

        return cleanup

    root.effect(setup, "reentrant-restart")
    await entered.wait()
    waiting = asyncio.create_task(root.fiber.wait())
    await asyncio.sleep(0)
    assert not waiting.done()
    setup_release.set()
    await cleanup_entered.wait()
    assert finished == ["setup"]
    assert not waiting.done()
    cleanup_release.set()
    await waiting
    assert finished == ["setup", "cleanup"]
    assert root.fiber.get_effects() == ()
    assert root.fiber.state is FiberState.ACTIVE


async def test_reentrant_restart_joins_async_rollback_after_sync_setup_error() -> None:
    root = Context()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def cleanup() -> None:
        entered.set()
        await release.wait()

    def setup() -> Generator[object, None, None]:
        yield cleanup
        root.fiber.restart()
        raise ValueError("setup failed after restart")

    with pytest.raises(ValueError, match="setup failed after restart"):
        root.effect(setup, "reentrant-throw")
    await entered.wait()
    waiting = asyncio.create_task(root.fiber.wait())
    await asyncio.sleep(0)
    assert not waiting.done()
    release.set()
    await waiting
    assert root.fiber.get_effects() == ()


async def test_parent_disposal_joins_pending_child_cleanup_without_running_setup() -> None:
    root = Context()
    owner = await root.plugin(lambda ctx, config: None)
    child = await owner.ctx.inject(["missing"], lambda ctx, config: pytest.fail("child ran"))
    entered = asyncio.Event()
    release = asyncio.Event()
    finished: list[bool] = []

    async def cleanup() -> None:
        entered.set()
        await release.wait()
        finished.append(True)

    child.ctx.effect(lambda: cleanup, "pending-child-cleanup")
    disposal = owner.dispose()
    await entered.wait()
    waiting = asyncio.create_task(owner.wait())
    await asyncio.sleep(0)
    assert not waiting.done()
    release.set()
    await disposal
    await waiting
    assert finished == [True]
    assert child.state is owner.state is FiberState.DISPOSED
    assert root.registry.size == 0


async def test_loading_parent_joins_child_cleanup_started_during_publication() -> None:
    root = Context()
    cleanup_started = asyncio.Event()
    cleanup_release = asyncio.Event()
    owner_disposal: Awaitable[None] | None = None
    child_disposal: Awaitable[None] | None = None
    owner_fiber: Fiber | None = None
    child_fiber: Fiber | None = None

    def observe(fiber: Fiber) -> None:
        nonlocal owner_disposal, child_disposal, child_fiber
        if fiber.name != "loading_child" or fiber.uid is None:
            return
        child_fiber = fiber

        async def cleanup() -> None:
            cleanup_started.set()
            await cleanup_release.wait()

        fiber.ctx.effect(lambda: cleanup, "loading-child-cleanup")
        assert owner_fiber is not None
        owner_disposal = owner_fiber.dispose()
        child_disposal = fiber.dispose()

    def loading_child(ctx: Context, config: object) -> None:
        pass

    def loading_owner(ctx: Context, config: object) -> None:
        nonlocal owner_fiber
        owner_fiber = ctx.fiber
        ctx.plugin(loading_child)

    root.on("internal/plugin", observe)
    owner_mount = root.plugin(loading_owner)
    await cleanup_started.wait()
    assert owner_disposal is not None and child_disposal is not None
    assert owner_fiber is not None
    waiting = asyncio.create_task(owner_fiber.wait())
    await asyncio.sleep(0)
    assert not waiting.done()
    cleanup_release.set()
    await asyncio.gather(owner_disposal, child_disposal, owner_mount, waiting)
    assert child_fiber is not None and child_fiber.uid is None
    assert owner_fiber.uid is None


async def test_parent_disposal_during_publication_drains_pending_child() -> None:
    root = Context()
    owner_ctx: Context | None = None

    def owner_plugin(ctx: Context, config: object) -> None:
        nonlocal owner_ctx
        owner_ctx = ctx

    owner = await root.plugin(owner_plugin)
    cleanup_started = asyncio.Event()
    cleanup_release = asyncio.Event()
    cleanup_finished: list[bool] = []
    child_calls: list[bool] = []
    parent_disposal: Awaitable[None] | None = None

    def register_pending_cleanup(fiber: Fiber) -> None:
        if fiber.name != "child_plugin" or fiber.uid is None:
            return

        async def cleanup() -> None:
            cleanup_started.set()
            await cleanup_release.wait()
            cleanup_finished.append(True)

        fiber.ctx.effect(lambda: cleanup, "pending-child-cleanup")

    def dispose_parent(fiber: Fiber) -> None:
        nonlocal parent_disposal
        if fiber.name == "child_plugin" and fiber.uid is not None:
            parent_disposal = owner.dispose()

    def child_plugin(ctx: Context, config: object) -> None:
        child_calls.append(True)

    root.on("internal/plugin", register_pending_cleanup)
    root.on("internal/plugin", dispose_parent)
    assert owner_ctx is not None
    child = owner_ctx.plugin(child_plugin)
    await cleanup_started.wait()
    assert parent_disposal is not None
    waiting = asyncio.create_task(owner.wait())
    await asyncio.sleep(0)
    assert not waiting.done()
    cleanup_release.set()
    await parent_disposal
    await waiting
    assert cleanup_finished == [True]
    assert child_calls == []
    assert child.state is owner.state is FiberState.DISPOSED
