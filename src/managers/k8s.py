#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Manager for handling K8s patches."""

import logging

from lightkube.core.client import Client
from lightkube.core.exceptions import ApiError
from lightkube.models.apps_v1 import StatefulSetSpec
from lightkube.models.core_v1 import Container, PodSpec, PodTemplateSpec
from lightkube.resources.apps_v1 import StatefulSet
from lightkube.types import PatchType

from literals import CONTAINER, SUBSTRATE

# default logging from lightkube httpx requests is very noisy
logging.getLogger("lightkube").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)


class K8sManager:
    """Object for handling K8s patches."""

    def __init__(
        self,
        pod_name: str,
        namespace: str,
        container: str = CONTAINER,
    ):
        self.pod_name = pod_name
        self.app_name = "-".join(pod_name.split("-")[:-1])
        self.namespace = namespace
        self.container = container
        self.substrate = SUBSTRATE

    @property
    def client(self) -> Client:
        """The Lightkube client."""
        return Client(  # pyright: ignore[reportArgumentType]
            field_manager=self.pod_name,
            namespace=self.namespace,
        )

    def disable_service_links(self) -> None:
        """Disables K8s service links for Pods in the application StatefulSet."""
        if self.substrate != "k8s":
            logger.debug("Application is not a K8s application, not disabling service links.")
            return

        sts = self._get_statefulset(sts_name=self.app_name)

        if not (sts.spec and sts.spec.selector and sts.spec.serviceName):
            raise Exception("Could not find StatefulSet spec parameters.")

        delta = StatefulSet(
            spec=StatefulSetSpec(
                selector=sts.spec.selector,
                serviceName=sts.spec.serviceName,
                template=PodTemplateSpec(
                    spec=PodSpec(
                        containers=[Container(name=self.container)], enableServiceLinks=False
                    )
                ),
            )
        )

        try:
            self.client.patch(StatefulSet, self.app_name, delta, patch_type=PatchType.APPLY)
        except ApiError as e:
            if e.status.code == 403:
                logger.error("Could not disable service links, application needs `juju trust`")
                return
            else:
                raise e

    def _get_statefulset(self, sts_name: str) -> StatefulSet:
        """Gets the StatefulSet of a given name via the K8s API."""
        return self.client.get(StatefulSet, name=sts_name)
