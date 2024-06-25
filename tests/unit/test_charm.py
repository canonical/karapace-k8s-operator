# Copyright 2024 Raul Zamora
# See LICENSE file for licensing details.
#
# Learn more about testing at: https://juju.is/docs/sdk/testing

import unittest

import ops
import ops.testing

from charm import KarapaceCharm


class TestCharm(unittest.TestCase):
    def setUp(self):
        self.harness = ops.testing.Harness(KarapaceCharm)
        self.addCleanup(self.harness.cleanup)

    def test_pebble_ready(self):
        pass
