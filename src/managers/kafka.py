#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Supporting objects for Kafka utils and management."""

import logging
import tempfile

from charms.kafka.v0.client import KafkaClient

from core.cluster import ClusterContext
from core.workload import WorkloadBase
from literals import KAFKA_TOPIC

logger = logging.getLogger(__name__)


class KafkaManager:
    """Object for handling Kafka."""

    def __init__(self, context: ClusterContext, workload: WorkloadBase) -> None:
        self.context = context
        self.workload = workload

    def brokers_active(self) -> bool:
        """Check that Kafka is active."""
        # Make a local copy for the tls related files.
        with tempfile.TemporaryDirectory() as tmp_dir:
            ca_file = open(mode="w", file=f"{tmp_dir}/ca")
            cert_file = open(mode="w", file=f"{tmp_dir}/cert")
            key_file = open(mode="w", file=f"{tmp_dir}/key")

            ca_file.write(self.context.server.ca)
            cert_file.write(self.context.server.certificate)
            key_file.write(self.context.server.private_key)

            ca_file.close()
            cert_file.close()
            key_file.close()

            client = KafkaClient(
                servers=self.context.kafka.bootstrap_servers.split(","),
                username=self.context.kafka.username,
                password=self.context.kafka.password,
                security_protocol=self.context.kafka.security_protocol,
                cafile_path=ca_file.name,
                certfile_path=cert_file.name,
                keyfile_path=key_file.name,
            )
            try:
                client.describe_topics([KAFKA_TOPIC])
            except Exception as e:
                logger.warning(e)
                return False
            return True
