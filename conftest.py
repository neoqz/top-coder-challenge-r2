import json
import pytest
from calculate_reimbursement import reimburse


@pytest.fixture(scope="session")
def data():
    with open("public_cases.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def formula_func():
    return lambda d, m, r: reimburse(d, m, r)


@pytest.fixture(scope="session")
def name():
    return "ML-rules"
