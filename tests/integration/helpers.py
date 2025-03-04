#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import logging
import socket
from contextlib import closing
from pathlib import Path
from subprocess import PIPE, check_output

import yaml
from pytest_operator.plugin import OpsTest

from literals import PORT

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
APP_NAME = METADATA["name"]
KARAPACE_CONTAINER = METADATA["resources"]["karapace-image"]["upstream-source"]

KAFKA = "kafka-k8s"
ZOOKEEPER = "zookeeper-k8s"
TLS_CERTIFICATES_OPERATOR = "tls-certificates-operator"
DUMMY_NAME = "app"


async def get_admin_credentials(ops_test: OpsTest, num_unit=0) -> str:
    """Use the charm action to retrieve the password for admin user.

    Return:
        String with the password stored on the peer relation databag.
    """
    action = await ops_test.model.units.get(f"{APP_NAME}/{num_unit}").run_action("get-password")
    password = await action.wait()
    return password.results["password"]


async def set_password(ops_test: OpsTest, username="operator", password=None, num_unit=0) -> str:
    """Use the charm action to start a password rotation."""
    params = {"username": username}
    if password:
        params["password"] = password

    action = await ops_test.model.units.get(f"{APP_NAME}/{num_unit}").run_action(
        "set-password", **params
    )
    password = await action.wait()
    return password.results


async def get_application_credentials(ops_test: OpsTest, role="user") -> tuple[str, str]:
    action = await ops_test.model.units.get(f"{DUMMY_NAME}/0").run_action(
        "get-credentials", **{"username": role}
    )
    credentials = await action.wait()
    return credentials.results["username"], credentials.results["password"]


async def set_tls_private_key(ops_test: OpsTest, key: str | None = None, num_unit=0):
    """Use the charm action to start a password rotation."""
    params = {"internal-key": key} if key else {}

    action = await ops_test.model.units.get(f"{APP_NAME}/{num_unit}").run_action(
        "set-tls-private-key", **params
    )
    return (await action.wait()).results


async def get_address(ops_test: OpsTest, app_name=APP_NAME, unit_num=0) -> str:
    """Get the address for a unit."""
    status = await ops_test.model.get_status()  # noqa: F821
    address = status["applications"][app_name]["units"][f"{app_name}/{unit_num}"]["address"]
    return address


def check_socket(host: str, port: int) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


async def assert_list_schemas(
    ops_test: OpsTest, expected_schemas: str = "[]", units: int = 1
) -> None:
    """Assert schemas can be listed."""
    operator_password = await get_admin_credentials(ops_test)
    for i in range(units):
        address = await get_address(ops_test=ops_test, unit_num=i)
        command = " ".join(
            [
                "curl",
                "-u",
                f"operator:{operator_password}",
                "-X",
                "GET",
                f"http://{address}:{PORT}/subjects",
            ]
        )

        logger.info("Requesting schemas")
        result = check_output(command, stderr=PIPE, shell=True, universal_newlines=True)
        assert expected_schemas in result
