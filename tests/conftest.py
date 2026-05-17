"""Shared pytest fixtures."""

import pandas as pd
import pytest

from tests.fixtures.fan_flow_fixtures import (
    build_fan_flow_accounts_fixture,
    build_joint_fan_in_and_fan_out_transactions_fixture,
)
from tests.fixtures.movement_dormancy_fixtures import (
    build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture,
    build_movement_dormancy_accounts_fixture,
)
from tests.fixtures.structuring_fixtures import (
    build_structuring_accounts_fixture,
    build_structuring_trigger_transactions_fixture,
)


@pytest.fixture
def structuring_accounts_fixture() -> pd.DataFrame:
    """Return deterministic account context for structuring tests."""

    return build_structuring_accounts_fixture()


@pytest.fixture
def structuring_trigger_transactions_fixture() -> pd.DataFrame:
    """Return deterministic trigger transactions for structuring tests."""

    return build_structuring_trigger_transactions_fixture()


@pytest.fixture
def fan_flow_accounts_fixture() -> pd.DataFrame:
    """Return deterministic account context for fan-flow tests."""

    return build_fan_flow_accounts_fixture()


@pytest.fixture
def joint_fan_flow_transactions_fixture() -> pd.DataFrame:
    """Return deterministic joint fan-in and fan-out transactions."""

    return build_joint_fan_in_and_fan_out_transactions_fixture()


@pytest.fixture
def movement_dormancy_accounts_fixture() -> pd.DataFrame:
    """Return deterministic account context for movement-dormancy tests."""

    return build_movement_dormancy_accounts_fixture()


@pytest.fixture
def joint_movement_dormancy_transactions_fixture() -> pd.DataFrame:
    """Return deterministic joint rapid movement and dormant reactivation transactions."""

    return build_joint_rapid_movement_and_dormant_reactivation_transactions_fixture()
