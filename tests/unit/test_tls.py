#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.

import socket
from pathlib import Path
from typing import cast
from unittest.mock import patch

import yaml
from ops.testing import Container, Context, Mount, State
from src.charm import KarapaceCharm
from src.literals import SUBSTRATE, Status

ACTIONS = str(yaml.safe_load(Path("./actions.yaml").read_text()))
METADATA = str(yaml.safe_load(Path("./metadata.yaml").read_text()))
CHARM_KEY = "karapace"
KAFKA = "kafka"


def test_blocked_before_tls_relation(
    ctx: Context, karapace_container, peer_relation_no_data, kafka_relation_tls
):
    state_in = State(
        containers=[karapace_container],
        relations=[peer_relation_no_data, kafka_relation_tls],
        leader=True,
    )
    state_out: State = ctx.run(ctx.on.config_changed(), state_in)

    assert state_out.unit_status == Status.KAFKA_TLS_MISMATCH.value.status


def test_sans_config(
    ctx: Context, karapace_container, peer_relation, kafka_relation_tls, tls_relation
):
    state_in = State(
        containers=[karapace_container],
        relations=[peer_relation, kafka_relation_tls, tls_relation],
        leader=True,
    )

    with ctx(ctx.on.config_changed(), state_in) as manager:
        # This is your charm instance, after ops has set it up:
        charm: KarapaceCharm = cast(KarapaceCharm, manager.charm)
        manager.run()

        sock_dns = socket.getfqdn()
        if SUBSTRATE == "vm":
            assert charm.tls._sans == {
                "sans_ip": ["treebeard"],
                "sans_dns": [f"{CHARM_KEY}/0", sock_dns],
            }
        elif SUBSTRATE == "k8s":
            # NOTE previous k8s sans_ip like karapace-k8s-0.karapace-k8s-endpoints or binding pod address
            with patch("ops.model.Model.get_binding"):
                assert charm.tls._sans["sans_dns"] == [
                    "karapace-k8s-0",
                    "karapace-k8s-0.karapace-k8s-endpoints",
                    sock_dns,
                ]


def test_tls_relation_broken_removes_stores(
    ctx: Context, karapace_container, peer_relation, kafka_relation_tls, tls_relation, tmp_path
):
    """TLS keys/certs are removed on relation-broken without relying on a shell glob."""
    conf_dir = tmp_path / "karapace"
    conf_dir.mkdir()
    tls_files = [conf_dir / name for name in ("cacert.pem", "cert.pem", "private.key")]
    other_file = conf_dir / "karapace.config.json"
    for f in [*tls_files, other_file]:
        f.write_text("content")

    container = Container(
        name=karapace_container.name,
        can_connect=True,
        layers=karapace_container.layers,
        service_statuses=karapace_container.service_statuses,
        mounts={"etc": Mount(location="/etc", source=tmp_path)},
    )
    state_in = State(
        containers=[container],
        relations=[peer_relation, kafka_relation_tls, tls_relation],
        leader=True,
    )
    ctx.run(ctx.on.relation_broken(tls_relation), state_in)

    assert not any(f.exists() for f in tls_files)
    assert other_file.exists()  # non-TLS files are kept
