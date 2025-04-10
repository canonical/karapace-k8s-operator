#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging
from subprocess import PIPE, check_output

import pytest
from helpers import (
    APP_NAME,
    KAFKA,
    KARAPACE_CONTAINER,
    ZOOKEEPER,
    assert_list_schemas,
    check_socket,
    get_address,
    get_admin_credentials,
)
from pytest_operator.plugin import OpsTest

from literals import PORT

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest, karapace_charm):
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    await ops_test.model.deploy(
        karapace_charm,
        application_name=APP_NAME,
        num_units=1,
        resources={"karapace-image": KARAPACE_CONTAINER},
        trust=True,
    )
    await ops_test.model.wait_for_idle(apps=[APP_NAME], idle_period=30, timeout=3600)
    assert ops_test.model.applications[APP_NAME].status == "blocked"


@pytest.mark.abort_on_fail
async def test_integrate_kafka(ops_test: OpsTest):
    """Integrate charm with Kafka."""
    await asyncio.gather(
        ops_test.model.deploy(ZOOKEEPER, channel="3/stable", application_name=ZOOKEEPER),
        ops_test.model.deploy(KAFKA, channel="3/stable", application_name=KAFKA),
    )
    await ops_test.model.wait_for_idle(apps=[ZOOKEEPER, KAFKA], idle_period=30, timeout=3600)

    await ops_test.model.add_relation(KAFKA, ZOOKEEPER)
    await ops_test.model.wait_for_idle(
        apps=[KAFKA, ZOOKEEPER],
        status="active",
        idle_period=30,
        timeout=1000,
        raise_on_error=False,
    )

    await ops_test.model.add_relation(KAFKA, APP_NAME)
    await ops_test.model.wait_for_idle(
        apps=[KAFKA, APP_NAME],
        status="active",
        idle_period=30,
        timeout=1000,
        raise_on_error=False,
    )


@pytest.mark.abort_on_fail
async def test_service(ops_test: OpsTest):
    """Check that port is open."""
    address = await get_address(ops_test=ops_test)
    assert check_socket(address, PORT)


@pytest.mark.abort_on_fail
async def test_schema_creation(ops_test: OpsTest):
    """Check that a schema can be registered using internal credentials."""
    operator_password = await get_admin_credentials(ops_test)
    address = await get_address(ops_test=ops_test)
    command = " ".join(
        [
            "curl",
            "-u",
            f"operator:{operator_password}",
            "-X",
            "POST",
            "-H",
            '"Content-Type: application/vnd.schemaregistry.v1+json"',
            "--data",
            '\'{"schema": "{\\"type\\": \\"record\\", \\"name\\": \\"Obj\\", \\"fields\\":[{\\"name\\": \\"age\\", \\"type\\": \\"int\\"}]}"}\'',
            f"http://{address}:{PORT}/subjects/test-key/versions",
        ]
    )

    result = check_output(command, stderr=PIPE, shell=True, universal_newlines=True)
    assert '{"id":1}' in result

    await assert_list_schemas(ops_test, expected_schemas='["test-key"]')


@pytest.mark.skip
@pytest.mark.abort_on_fail
async def test_scale_up_kafka(ops_test: OpsTest):
    """Scale up Kafka charm."""
    await ops_test.model.applications[KAFKA].add_units(count=2)
    await ops_test.model.wait_for_idle(apps=[ZOOKEEPER, KAFKA, APP_NAME])

    assert ops_test.model.applications[APP_NAME].status == "active"

    # Schema added on the previous test, checks that karapace is still working
    await assert_list_schemas(ops_test, expected_schemas='["test-key"]')


@pytest.mark.abort_on_fail
async def test_scale_up(ops_test: OpsTest):
    """Scale up Karapace charm."""
    await ops_test.model.applications[APP_NAME].scale(scale=3)
    await ops_test.model.wait_for_idle(apps=[KAFKA, APP_NAME])

    assert ops_test.model.applications[APP_NAME].status == "active"

    # Schema added on the previous test, checks that karapace is still working
    await assert_list_schemas(ops_test, expected_schemas='["test-key"]', units=3)


@pytest.mark.abort_on_fail
async def test_scale_down(ops_test: OpsTest):
    """Scale down Karapace charm."""
    await ops_test.model.applications[APP_NAME].scale(scale=1)
    await ops_test.model.wait_for_idle(apps=[KAFKA, APP_NAME], wait_for_exact_units=1)

    assert ops_test.model.applications[APP_NAME].status == "active"

    # Schema added on the previous test, checks that karapace is still working
    await assert_list_schemas(ops_test, expected_schemas='["test-key"]')
