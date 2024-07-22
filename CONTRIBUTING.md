# Contributing

## Overview

This documents explains the processes and practices recommended for contributing enhancements to this operator.

- Generally, before developing enhancements to this charm, you should consider [opening an issue](https://github.com/canonical/karapace-k8s-operator/issues) explaining your problem with examples, and your desired use case.
- If you would like to chat with us about your use-cases or proposed implementation, you can reach us at [Canonical Matrix public channel](https://matrix.to/#/#charmhub-data-platform:ubuntu.com) or [Discourse](https://discourse.charmhub.io/).
- Familiarising yourself with the [Charmed Operator Framework](https://juju.is/docs/sdk) library will help you a lot when working on new features or bug fixes.
- All enhancements require review before being merged. Code review typically examines
  - code quality
  - test coverage
  - user experience for Juju administrators of this charm.
- Please help us out in ensuring easy to review branches by rebasing your pull request branch onto the `main` branch. This also avoids merge commits and creates a linear Git commit history.

## Requirements

To build the charm locally, you will need to install [Charmcraft](https://juju.is/docs/sdk/install-charmcraft).

To run the charm locally with Juju, it is recommended to use [Microk8s](https://microk8s.io/docs) as your virtual machine manager. Instructions for running Juju on Microk8s can be found [here](https://juju.is/docs/juju/microk8s).

## Build and Deploy

To build the charm in this repository, from the root of the dir you can run:

### Deploy

```bash
# Clone and enter the repository
git clone https://github.com/canonical/karapace-k8s-operator.git
cd karapace-k8s-operator/

# Create a working model
juju add-model karapace

# Enable DEBUG logging for the model
juju model-config logging-config="<root>=INFO;unit=DEBUG"

# Build the charm locally
charmcraft pack

# Deploy the latest ZooKeeper release
juju deploy zookeeper-k8s --channel edge

# Deploy the latest Kafka release
juju deploy kafka-k8s --channel edge

# Deploy the charm
juju deploy ./*.charm --resource karapace-image=<value on metadata.yaml "upstream-source">

# Integrate Kafka and ZooKeeper
juju integrate kafka-k8s zookeeper-k8s

# Integrate with Karapace
juju integrate karapace-k8s kafka-k8s
```

## Developing

You can create an environment for development with `tox`:

```shell
tox devenv -e integration
source venv/bin/activate
```

### Testing

```shell
tox run -e format        # update your code according to linting rules
tox run -e lint          # code style
tox run -e unit          # unit tests
tox run -e integration   # integration tests
tox                      # runs 'lint' and 'unit' environments
```

## Canonical Contributor Agreement

Canonical welcomes contributions to the Charmed Karapace K8s Operator. Please check out our [contributor agreement](https://ubuntu.com/legal/contributors) if you're interested in contributing to the solution.
