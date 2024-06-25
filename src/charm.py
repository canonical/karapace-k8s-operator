#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm the application."""

import logging

import ops
from charms.data_platform_libs.v0.data_models import TypedCharmBase
from charms.rolling_ops.v0.rollingops import RollingOpsManager
from ops.pebble import Layer, LayerDict

from core.cluster import ClusterContext
from core.structured_config import CharmConfig
from events.kafka import KafkaHandler
from events.password_actions import PasswordActionEvents
from events.provider import KarapaceHandler
from events.tls import TLSHandler
from literals import CHARM_KEY, CONTAINER, GROUP, USER, DebugLevel, Status, Substrate
from managers.auth import KarapaceAuth
from managers.config import ConfigManager
from managers.kafka import KafkaManager
from managers.tls import TLSManager
from workload import KarapaceWorkload

logger = logging.getLogger(__name__)


class KarapaceCharm(TypedCharmBase[CharmConfig]):
    """Charmed Operator for Karapace."""

    config_type = CharmConfig

    def __init__(self, *args):
        super().__init__(*args)

        self.name = CHARM_KEY
        self.substrate: Substrate = "k8s"
        self.context = ClusterContext(charm=self, substrate=self.substrate)
        self.workload = KarapaceWorkload(container=self.unit.get_container(CONTAINER))

        # HANDLERS

        self.password_action_events = PasswordActionEvents(self)
        self.kafka = KafkaHandler(self)
        self.tls = TLSHandler(self)
        self.provider = KarapaceHandler(self)

        # MANAGERS

        self.config_manager = ConfigManager(context=self.context, workload=self.workload)
        self.auth_manager = KarapaceAuth(context=self.context, workload=self.workload)
        self.tls_manager = TLSManager(context=self.context, workload=self.workload)
        self.kafka_manager = KafkaManager(context=self.context, workload=self.workload)

        # LIB HANDLERS

        self.restart = RollingOpsManager(self, relation="restart", callback=self._restart)

        # CORE EVENTS

        self.framework.observe(self.on.install, self._on_install)
        # self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(
            getattr(self.on, "karapace_pebble_ready"), self._on_karapace_pebble_ready
        )
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.update_status, self._on_update_status)

    @property
    def karapace_layer(self) -> Layer:
        """Returns a Pebble configuration layer for Karapace."""
        command = f"karapace {self.workload.paths.karapace_config}"

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
                }
            },
        }
        return Layer(layer_config)

    def _on_install(self, event: ops.InstallEvent):
        """Handle install event."""
        if not self.unit.get_container(CONTAINER).can_connect():
            event.defer()
            return

        self.unit.set_workload_version(self.workload.get_version())

    # def _on_start(self, event: ops.EventBase):
    #     """Handle start event."""
    #     self._on_karapace_pebble_ready(event)

    def _on_karapace_pebble_ready(self, event: ops.EventBase) -> None:
        """Handle pebble ready event."""
        if not self.context.peer_relation:
            self._set_status(Status.NO_PEER_RELATION)
            event.defer()
            return

        if not self.workload.container_can_connect():
            self._set_status(Status.CONTAINER_NOT_CONNECTED)
            event.defer()
            return

        if self.context.cluster.internal_user_credentials:
            self.auth_manager.update_admin_user()
        elif self.unit.is_leader():
            self.auth_manager.create_internal_user()
        else:
            # Unit is not leader and there are no internal credentials added yet
            event.defer()
            return

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle config changed event."""
        self._set_status(self.context.ready_to_start)
        if not isinstance(self.unit.status, ops.ActiveStatus):
            event.defer()
            return

        # Load current properties set in the charm workload
        rendered_file = self.config_manager.parsed_confile
        if rendered_file != self.config_manager.config:
            logger.info(
                (
                    f'Server {self.unit.name.split("/")[1]} updating config - '
                    f"OLD CONFIG = {set(rendered_file.items()) - set(self.config_manager.config.items())}, "
                    f"NEW CONFIG = {set(self.config_manager.config.items()) - set(rendered_file.items())}"
                )
            )

            # Config is different, apply changes to file
            self.config_manager.generate_config()

            # Restart so changes take effect
            self.on[f"{self.restart.name}"].acquire_lock.emit()

        self.unit.status = ops.ActiveStatus()

    def _on_update_status(self, _: ops.UpdateStatusEvent):
        """Handle update status."""
        if not self.healthy:
            return

        if not self.kafka_manager.brokers_active():
            self._set_status(Status.KAFKA_NOT_CONNECTED)
            return

        self.on.config_changed.emit()

    def _restart(self, _: ops.EventBase) -> None:
        """Handler for emitted restart events."""
        # only attempt restart if service is already active
        if not self.healthy:
            # event.defer()
            return

        self.workload.restart()

        if self.workload.active():
            logger.info(f"{self.unit.name} restarted")
        else:
            logger.error(f"{self.unit.name} failed to restart")

    @property
    def healthy(self) -> bool:
        """Checks and updates various charm lifecycle states.

        Is slow to fail due to retries, to be used sparingly.

        Returns:
            True if service is alive and active. Otherwise False
        """
        self._set_status(self.context.ready_to_start)
        if not isinstance(self.unit.status, ops.ActiveStatus):
            return False

        if not self.workload.active():
            self._set_status(Status.SERVICE_NOT_RUNNING)
            return False

        return True

    def _set_status(self, key: Status) -> None:
        """Sets charm status."""
        status: ops.StatusBase = key.value.status
        log_level: DebugLevel = key.value.log_level

        getattr(logger, log_level.lower())(status.message)
        self.unit.status = status


if __name__ == "__main__":  # pragma: nocover
    ops.main(KarapaceCharm)  # type: ignore