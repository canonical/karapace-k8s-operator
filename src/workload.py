#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Karapace workload class and methods."""

import logging
import re

from ops import Container
from ops.pebble import ExecError, Layer, LayerDict
from tenacity import retry, retry_if_result, stop_after_attempt, wait_fixed
from typing_extensions import override

from core.workload import WorkloadBase
from literals import CONTAINER, GROUP, SALT, USER

logger = logging.getLogger(__name__)


class KarapaceWorkload(WorkloadBase):
    """Wrapper for performing common operations specific to the Karapace Snap."""

    CONTAINER_SERVICE = "karapace"

    def __init__(self, container: Container) -> None:
        self.container = container

    @override
    def start(self) -> None:
        self.container.add_layer(self.CONTAINER_SERVICE, self._karapace_layer, combine=True)
        self.container.replan()

    @override
    def stop(self) -> None:
        self.container.stop(self.CONTAINER_SERVICE)

    @override
    def restart(self) -> None:
        self.container.restart(self.CONTAINER_SERVICE)

    @override
    def read(self, path: str) -> list[str]:
        if not self.container_can_connect() or not self.container.exists(path):
            return []
        else:
            with self.container.pull(path) as f:
                content = f.read().split("\n")

        return content

    @override
    def write(self, content: str, path: str) -> None:
        self.container.push(path, content, make_dirs=True)

    @override
    def exec(
        self, command: str, env: dict[str, str] | None = None, working_dir: str | None = None
    ) -> str:
        try:
            process = self.container.exec(
                command=command.split(),
                environment=env,
                working_dir=working_dir,
                combine_stderr=True,
            )
            output, _ = process.wait_output()
            return output
        except ExecError as e:
            logger.debug(e)
            raise e

    @retry(
        wait=wait_fixed(1),
        stop=stop_after_attempt(5),
        retry=retry_if_result(lambda result: result is False),
        retry_error_callback=lambda _: False,
    )
    @override
    def active(self) -> bool:
        if not self.container.can_connect():
            return False

        return self.container.get_service(self.CONTAINER_SERVICE).is_running()

    @override
    def get_version(self) -> str:
        if not self.active:
            return ""
        try:
            version = re.split(r"[\s\-]", self.exec(command="karapace --version"))[0]
        except:  # noqa: E722
            version = ""
        return version

    @override
    def mkpasswd(self, username: str, password: str) -> str:
        return self.exec(command=f"karapace_mkpasswd -u {username} -a sha512 {password} {SALT}")

    def container_can_connect(self) -> bool:
        """Check if karapace container is available."""
        return self.container.can_connect()

    @property
    def _karapace_layer(self) -> Layer:
        """Returns a Pebble configuration layer for Karapace."""
        environment = self.map_env(self.read("/etc/environment"))
        command = "python3 -m karapace"

        layer_config: LayerDict = {
            "summary": "karapace layer",
            "description": "Pebble config layer for karapace",
            "services": {
                CONTAINER: {
                    "override": "replace",
                    "summary": "karapace",
                    "command": command,
                    "startup": "enabled",
                    "user": USER,
                    "group": GROUP,
                    "environment": environment,
                }
            },
        }
        return Layer(layer_config)
