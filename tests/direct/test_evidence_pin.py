import json

import pytest

URL = "https://status.acme.example/cloud"

PAGE_A = """
Acme Cloud Status
Service level: the uptime target for the hosted API is 99.9% measured monthly
across all regions. Last incident: none reported in the past 90 days. Support
responses are sent within one business day. This page is the authoritative
public statement of the service level for the hosted API.
"""

QUOTE_A = "the uptime target for the hosted API is 99.9% measured monthly"

PAGE_B = """
Acme Cloud Status
Service level: the uptime target for the hosted API is 99.5% measured monthly
across all regions, revised after the February maintenance window. Support
responses are sent within one business day. This page remains the authoritative
public statement of the service level for the hosted API.
"""

QUOTE_B = "the uptime target for the hosted API is 99.5% measured monthly"

PAGE_C = """
Acme Cloud Careers
We are hiring engineers in three offices. Benefits include a learning budget, a
public transport pass, and twenty-eight days of paid leave. Our interview
process has four stages and takes about three weeks from first contact.
"""

OPTIONS = ["99.9", "99.5"]
QUESTION = "What monthly uptime target does the status page publish for the hosted API?"

LLM_PATTERN = r"(?s).*Acme Cloud.*"

def _llm(answer, quote):
    return json.dumps({"answer": answer, "quote": quote})

@pytest.fixture
def contract(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_A})
    direct_vm.mock_llm(LLM_PATTERN, _llm("99.9", QUOTE_A))
    return direct_deploy("contracts/evidence_pin.py")

def test_pin_happy_path(contract, direct_alice):
    pin_id = contract.pin(URL, QUESTION, OPTIONS)

    assert pin_id == "P1"
    pin = contract.get_pin(pin_id)
    assert pin["status"] == "ACTIVE"
    assert pin["reason"] == "PINNED"
    assert pin["answer"] == "99.9"
    assert pin["quote"] == QUOTE_A
    assert pin["version"] == 1
    assert pin["checks"] == 0
    assert pin["options"] == "99.9|99.5"
    assert pin["owner"].lower() == "0x" + direct_alice.hex()
    assert contract.count() == 1
    assert contract.is_active(pin_id) is True

def test_pin_rejects_paraphrased_quote(direct_vm, contract):
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_A})
    direct_vm.mock_llm(
        LLM_PATTERN,
        _llm("99.9", "the API is targeted to stay up 99.9 percent of every month"),
    )

    with direct_vm.expect_revert("QUOTE_NOT_GROUNDED"):
        contract.pin(URL, QUESTION, OPTIONS)

    assert contract.count() == 0

def test_pin_rejects_unknown_answer(direct_vm, contract):
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_C})
    direct_vm.mock_llm(LLM_PATTERN, _llm("UNKNOWN", ""))

    with direct_vm.expect_revert("NO_GROUNDED_ANSWER"):
        contract.pin(URL, QUESTION, OPTIONS)

def test_pin_rejects_unreadable_source(direct_vm, contract):
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": "Loading"})

    with direct_vm.expect_revert("SOURCE_EMPTY_OR_UNREADABLE"):
        contract.pin(URL, QUESTION, OPTIONS)

def test_pin_input_validation(contract):
    with pytest.raises(Exception):
        contract.pin("http://status.acme.example/cloud", QUESTION, OPTIONS)
    with pytest.raises(Exception):
        contract.pin(URL, "short", OPTIONS)
    with pytest.raises(Exception):
        contract.pin(URL, QUESTION, ["only-one"])
    with pytest.raises(Exception):
        contract.pin(URL, QUESTION, ["99.9", "99.9"])
    with pytest.raises(Exception):
        contract.pin(URL, QUESTION, ["99.9", "UNKNOWN"])

def test_validator_accepts_leader_when_both_are_grounded(direct_vm, contract):
    contract.pin(URL, QUESTION, OPTIONS)
    assert direct_vm.run_validator() is True

def test_validator_rejects_quote_missing_from_its_own_copy(direct_vm, contract):
    contract.pin(URL, QUESTION, OPTIONS)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_B})
    direct_vm.mock_llm(LLM_PATTERN, _llm("99.5", QUOTE_B))

    assert direct_vm.run_validator() is False

def test_validator_rejects_label_disagreement(direct_vm, contract):
    contract.pin(URL, QUESTION, OPTIONS)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_A})
    direct_vm.mock_llm(LLM_PATTERN, _llm("99.5", QUOTE_A))

    assert direct_vm.run_validator() is False

def test_recheck_present_is_deterministic(direct_vm, contract):
    pin_id = contract.pin(URL, QUESTION, OPTIONS)

    # No LLM mock left: if recheck called a model this would fail.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_A})

    status = contract.recheck(pin_id)

    pin = contract.get_pin(pin_id)
    assert status == "ACTIVE"
    assert pin["reason"] == "PRESENT"
    assert pin["version"] == 1
    assert pin["checks"] == 1

def test_recheck_changed_creates_new_version(direct_vm, contract):
    pin_id = contract.pin(URL, QUESTION, OPTIONS)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_B})
    direct_vm.mock_llm(LLM_PATTERN, _llm("99.5", QUOTE_B))

    assert contract.recheck(pin_id) == "ACTIVE"

    pin = contract.get_pin(pin_id)
    assert pin["reason"] == "CHANGED"
    assert pin["version"] == 2
    assert pin["answer"] == "99.5"
    assert pin["quote"] == QUOTE_B
    assert pin["checks"] == 1

def test_recheck_not_found_never_claims_false(direct_vm, contract):
    pin_id = contract.pin(URL, QUESTION, OPTIONS)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_B})
    direct_vm.mock_llm(LLM_PATTERN, _llm("UNKNOWN", ""))

    assert contract.recheck(pin_id) == "NOT_FOUND"

    pin = contract.get_pin(pin_id)
    assert pin["status"] == "NOT_FOUND"
    assert pin["reason"] == "NOT_FOUND"
    assert pin["version"] == 1
    assert pin["quote"] == QUOTE_A
    assert contract.is_active(pin_id) is False

def test_recheck_tolerates_fetch_failure(direct_vm, contract):
    pin_id = contract.pin(URL, QUESTION, OPTIONS)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 503, "body": ""})

    assert contract.recheck(pin_id) == "ACTIVE"
    pin = contract.get_pin(pin_id)
    assert pin["reason"] == "FETCH_FAILED"
    assert pin["checks"] == 1

def test_close_is_owner_only(contract, direct_vm, direct_alice, direct_bob):
    pin_id = contract.pin(URL, QUESTION, OPTIONS)

    direct_vm.sender = direct_bob
    with direct_vm.expect_revert("ONLY_OWNER_CAN_CLOSE"):
        contract.close(pin_id)

    direct_vm.sender = direct_alice
    contract.close(pin_id)
    assert contract.is_active(pin_id) is False
    assert contract.get_pin(pin_id)["status"] == "CLOSED"

    with direct_vm.expect_revert("PIN_CLOSED"):
        contract.recheck(pin_id)

def test_validator_rejects_label_outside_allowed_set(direct_vm, contract):
    contract.pin(URL, QUESTION, OPTIONS)

    # Simulate a leader that injected a label the caller never allowed.
    assert direct_vm.run_validator(leader_result={"answer": "99.0", "quote": QUOTE_A}) is False

def test_recheck_recovers_from_not_found(direct_vm, contract):
    pin_id = contract.pin(URL, QUESTION, OPTIONS)

    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_C})
    direct_vm.mock_llm(LLM_PATTERN, _llm("UNKNOWN", ""))
    assert contract.recheck(pin_id) == "NOT_FOUND"

    # The source comes back with a grounded answer: the pin recovers.
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*status\.acme\.example.*", {"status": 200, "body": PAGE_B})
    direct_vm.mock_llm(LLM_PATTERN, _llm("99.5", QUOTE_B))

    assert contract.recheck(pin_id) == "ACTIVE"
    pin = contract.get_pin(pin_id)
    assert pin["status"] == "ACTIVE"
    assert pin["reason"] == "CHANGED"
    assert pin["version"] == 2
    assert pin["quote"] == QUOTE_B
    assert pin["checks"] == 2

def test_pin_rejects_more_than_five_options(contract):
    with pytest.raises(Exception):
        contract.pin(URL, QUESTION, ["a", "b", "c", "d", "e", "f"])

def test_unknown_pin(contract):
    with pytest.raises(Exception):
        contract.get_pin("P404")
    with pytest.raises(Exception):
        contract.recheck("P404")
