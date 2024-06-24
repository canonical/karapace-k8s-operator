# Charmed Karapace K8s Operator

[![CharmHub Badge](https://charmhub.io/karapace-k8s/badge.svg)](https://charmhub.io/karapace-k8s)
[![Release](https://github.com/canonical/karapace-k8s-operator/actions/workflows/release.yaml/badge.svg)](https://github.com/canonical/karapace-k8s-operator/actions/workflows/release.yaml)
[![Tests](https://github.com/canonical/karapace-k8s-operator/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/canonical/karapace-k8s-operator/actions/workflows/ci.yaml?query=branch%3Amain)
[![Docs](https://github.com/canonical/karapace-k8s-operator/actions/workflows/sync_docs.yaml/badge.svg)](https://github.com/canonical/karapace-k8s-operator/actions/workflows/sync_docs.yaml)

## Overview

The Charmed Karapace K8s Operator delivers automated operations management from day 0 to day 2 on [Karapace](https://www.karapace.io/).

This operator can be found on [Charmhub](https://charmhub.io/karapace) and it comes with production-ready features such as:
- Fault-tolerance, replication and scalability out-of-the-box.
- Authentication of users.
- Access control management supported with user-provided ACL lists.

The Karapace K8s Operator uses the latest upstream Karapace package released, made available using the [`charmed-karapace` rock](https://github.com/canonical/charmed-karapace-rock) distributed by Canonical.

As Karapace requires a running Kafka cluster, this operator makes use of the [Kafka K8s Operator](https://github.com/canonical/kafka-k8s-operator) in order to work.


## Usage

### Basic usage

Before using Karapace, a Kafka cluster needs to be deployed. The Kafka and ZooKeeper operators can both be deployed as follows:
```shell
$ juju deploy zookeeper-k8s --channel latest/edge -n 5
$ juju deploy kafka-k8s --channel latest/edge -n 3
```

After this, it is necessary to connect them:
```shell
$ juju integrate kafka-k8s zookeeper-k8s
```

To watch the process, `juju status` can be used. Once all the units show as `active|idle` Karapace can be connected with Kafka:

```shell
$ juju deploy karapace-k8s --channel latest/edge
$ juju integrate karapace-k8s kafka-k8s
```

The credentials to access the server can be queried with:
```shell
juju run karapace-k8s/leader get-password username="operator"
```

With these credentials, the server can be queried now. An example showing all registered schemas:
```shell
$ curl -u operator:<password> -X GET http://localhost:8081/subjects
```

### Password rotation
#### Internal operator user
The operator user is used internally by the Charmed Karapace K8s Operator, the `set-password` action can be used to rotate its password.
```shell
# to set a specific password for the operator user
juju run karapace-k8s/leader set-password password=<password>

# to randomly generate a password for the operator user
juju run karapace-k8s/leader set-password
```

## Relations

Supported [relations](https://juju.is/docs/olm/relations):

#### `karapace_client` interface:

The `karapace_client` interface is used with any requirer charm. This interface will allow to create users and acls. At the moment the interface can be found under `/src/relations/karapace.py`

#### `tls-certificates` interface:

The `tls-certificates` interface is used with the `tls-certificates-operator` charm.

To enable TLS:

```shell
# deploy the TLS charm
juju deploy tls-certificates-operator --channel=edge
# add the necessary configurations for TLS
juju config tls-certificates-operator generate-self-signed-certificates="true" ca-common-name="Test CA"
# to enable TLS relate the applications
juju integrate tls-certificates-operator zookeeper-k8s
juju integrate tls-certificates-operator kafka-k8s:certificates
juju integrate tls-certificates-operator karapace-k8s
```

Updates to private keys for certificate signing requests (CSR) can be made via the `set-tls-private-key` action.
```shell
# Updates can be done with auto-generated keys with
juju run karapace-k8s/0 set-tls-private-key
```

To disable TLS remove the relation
```shell
juju remove-relation karapace-k8s tls-certificates-operator
juju remove-relation kafka-k8s tls-certificates-operator
juju remove-relation zookeeper-k8s tls-certificates-operator
```

Note: The TLS settings here are for self-signed-certificates which are not recommended for production clusters, the `tls-certificates-operator` charm offers a variety of configurations, read more on the TLS charm [here](https://charmhub.io/tls-certificates-operator)


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this charm following best practice guidelines, and [CONTRIBUTING.md](https://github.com/canonical/karapace-k8s-operator/blob/main/CONTRIBUTING.md) for developer guidance. 

### We are Hiring!

Also, if you truly enjoy working on open-source projects like this one and you would like to be part of the OSS revolution, please don't forget to check out the [open positions](https://canonical.com/careers/all) we have at [Canonical](https://canonical.com/). 

## License
The Charmed Karapace K8s Operator is free software, distributed under the Apache Software License, version 2.0. See [LICENSE](https://github.com/canonical/karapace-k8s-operator/blob/main/LICENSE) for more information.
