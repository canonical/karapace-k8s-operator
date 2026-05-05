#!/usr/bin/env python3
# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import os
from pathlib import Path

import pytest
from jubilant_adapters import JujuFixture, temp_model_fixture


def pytest_addoption(parser):
    """Defines pytest parsers."""
    parser.addoption(
        "--model",
        action="store",
        help="Juju model to use; if not provided, a new model "
        "will be created for each test which requires one",
    )
    parser.addoption(
        "--keep-models",
        action="store_true",
        help="Keep models handled by opstest, can be overridden in track_model",
    )
    parser.addoption("--kafka", action="store", help="Kafka version", default="3")


@pytest.fixture(scope="module")
def kafka_version(request: pytest.FixtureRequest) -> int:
    """Returns the Kafka version used for tests`."""
    val = f'{request.config.getoption("--kafka")}' or "3"
    if val not in ("3", "4"):
        raise Exception("Unknown Kafka version, valid options are 3 and 4")

    return int(val)


@pytest.fixture(scope="module")
def juju(request: pytest.FixtureRequest):
    """Pytest fixture that wraps :meth:`jubilant.with_model`.

    This adds command line parameter ``--keep-models`` (see help for details).
    """
    model = request.config.getoption("--model")
    keep_models = bool(request.config.getoption("--keep-models"))

    if model:
        juju = JujuFixture(model=model)
        yield juju
    else:
        with temp_model_fixture(keep=keep_models) as juju:
            yield juju


@pytest.fixture(scope="module", autouse=True)
def switch_model(juju: JujuFixture):
    if not juju.model:
        return

    juju.cli("switch", juju.model, include_model=False)


@pytest.fixture(scope="module")
def karapace_charm(juju: JujuFixture) -> Path:
    """Kafka charm used for integration testing."""
    charm = juju.ext.build_charm(".", use_cache=bool(os.environ.get("CI")))
    return charm


@pytest.fixture(scope="module")
def app_charm(juju: JujuFixture) -> Path:
    """Build the application charm."""
    charm_path = "tests/integration/app-charm"
    charm = juju.ext.build_charm(charm_path, use_cache=bool(os.environ.get("CI")))
    return charm
