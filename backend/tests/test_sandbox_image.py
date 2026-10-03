"""Pinned sandbox image presence checks across Docker reference forms."""

from __future__ import annotations

import subprocess


def test_image_references_add_digest_form_without_touching_registry_ports() -> None:
    from app.execution.sandbox import image_references

    pinned = "python:3.14-alpine@sha256:" + "a" * 64
    assert image_references(pinned) == [pinned, "python@sha256:" + "a" * 64]
    ported = "registry.local:5000/team/python@sha256:" + "b" * 64
    assert image_references(ported) == [ported]
    tagged = "registry.local:5000/python:3.14@sha256:" + "c" * 64
    assert image_references(tagged)[1] == "registry.local:5000/python@sha256:" + "c" * 64
    assert image_references("python:3.14-alpine") == ["python:3.14-alpine"]


def test_image_available_falls_back_to_digest_reference(monkeypatch) -> None:
    from app.execution import sandbox as module

    pinned = "python:3.14-alpine@sha256:" + "a" * 64
    seen: list[str] = []

    def fake_run(command, **kwargs):
        seen.append(command[-1])
        code = 0 if command[-1] == "python@sha256:" + "a" * 64 else 1
        return subprocess.CompletedProcess(command, code, b"", b"")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    assert module.image_available(pinned)
    assert seen == [pinned, "python@sha256:" + "a" * 64]

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 1, b"", b""),
    )
    assert not module.image_available(pinned)

    def unavailable(command, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(module.subprocess, "run", unavailable)
    assert not module.image_available(pinned)


def test_image_available_uses_digest_listing_when_inspect_refuses_pins(monkeypatch) -> None:
    from app.execution import sandbox as module

    pinned = "python:3.14-alpine@sha256:" + "a" * 64

    def listing(stdout: bytes):
        def fake_run(command, **kwargs):
            if command[1:3] == ["image", "inspect"]:
                return subprocess.CompletedProcess(command, 1, b"", b"No such image")
            return subprocess.CompletedProcess(command, 0, stdout, b"")

        return fake_run

    monkeypatch.setattr(module.subprocess, "run", listing(b"python@sha256:" + b"a" * 64 + b"\n"))
    assert module.image_available(pinned)
    # A different digest under the same tag never satisfies the pin.
    monkeypatch.setattr(module.subprocess, "run", listing(b"python@sha256:" + b"b" * 64 + b"\n"))
    assert not module.image_available(pinned)
    # Unpinned references are not satisfied by the digest listing.
    assert not module.image_available("python:3.14-alpine")
