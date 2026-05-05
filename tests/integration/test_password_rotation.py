#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.
import logging
from time import sleep

from helpers import (
    APP_NAME,
    KAFKA,
    KARAPACE_CONTAINER,
    ZOOKEEPER,
    get_admin_credentials,
    set_password,
)
from jubilant_adapters import JujuFixture, gather

logger = logging.getLogger(__name__)


def test_build_and_deploy(juju: JujuFixture, karapace_charm):
    gather(
        juju.ext.model.deploy(
            karapace_charm,
            application_name=APP_NAME,
            num_units=1,
            resources={"karapace-image": KARAPACE_CONTAINER},
            trust=True,
        ),
        juju.ext.model.deploy(ZOOKEEPER, channel="3/stable", application_name=ZOOKEEPER),
        juju.ext.model.deploy(KAFKA, channel="3/stable", application_name=KAFKA),
    )

    juju.ext.model.add_relation(KAFKA, ZOOKEEPER)
    juju.ext.model.wait_for_idle(
        apps=[KAFKA, ZOOKEEPER],
        status="active",
        idle_period=30,
        timeout=1000,
        raise_on_error=False,
    )

    juju.ext.model.add_relation(KAFKA, APP_NAME)

    with juju.ext.fast_forward(fast_interval="60s"):
        sleep(180)

    juju.ext.model.wait_for_idle(apps=[KAFKA, APP_NAME], idle_period=30, timeout=1800)

    assert juju.ext.model.applications[APP_NAME].status == "active"


def test_password_rotation(juju: JujuFixture):
    """Check that password stored on Karapace has changed after a password rotation."""
    initial_operator_password = get_admin_credentials(juju)

    result = set_password(juju, username="operator", num_unit=0)
    assert "operator-password" in result.keys()

    juju.ext.model.wait_for_idle(apps=[APP_NAME])

    new_operator_user = get_admin_credentials(juju)

    assert initial_operator_password != new_operator_user
