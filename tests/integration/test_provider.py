#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import asyncio
import logging

import pytest
from helpers import APP_NAME, DUMMY_NAME, KAFKA, KARAPACE_CONTAINER, ZOOKEEPER
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)


@pytest.mark.abort_on_fail
@pytest.mark.skip_if_deployed
async def test_build_and_deploy(ops_test: OpsTest, karapace_charm, app_charm):
    await asyncio.gather(
        ops_test.model.deploy(
            karapace_charm,
            application_name=APP_NAME,
            num_units=1,
            resources={"karapace-image": KARAPACE_CONTAINER},
        ),
        ops_test.model.deploy(ZOOKEEPER, channel="3/stable", application_name=ZOOKEEPER),
        ops_test.model.deploy(KAFKA, channel="3/stable", application_name=KAFKA),
        ops_test.model.deploy(app_charm, application_name=DUMMY_NAME, num_units=1),
    )

    await ops_test.model.add_relation(KAFKA, ZOOKEEPER)
    await ops_test.model.wait_for_idle(apps=[KAFKA, ZOOKEEPER])

    assert ops_test.model.applications[KAFKA].status == "active"
    assert ops_test.model.applications[ZOOKEEPER].status == "active"

    await ops_test.model.add_relation(KAFKA, APP_NAME)
    await ops_test.model.wait_for_idle(apps=[KAFKA, APP_NAME, DUMMY_NAME])

    assert ops_test.model.applications[APP_NAME].status == "active"


@pytest.mark.abort_on_fail
async def test_relate_requirer(ops_test: OpsTest):
    await ops_test.model.add_relation(APP_NAME, f"{DUMMY_NAME}:karapace-client-admin")
    await ops_test.model.wait_for_idle(apps=[APP_NAME, DUMMY_NAME])

    assert ops_test.model.applications[APP_NAME].status == "active"
    assert ops_test.model.applications[DUMMY_NAME].status == "active"
