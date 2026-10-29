# EvidencePin

A reusable GenLayer Intelligent Contract primitive for **quote-grounded, point-in-time evidence** with verifiable freshness.

Web-judging contracts rot. A leader reads a page at block N, a verdict is stored, and
months later the page has changed and nobody can tell. EvidencePin stores the smallest
durable unit of evidence — a **verbatim quote** plus the **closed-set answer** it supports —
and later answers one honest question: *is this evidence still there, and if not, what does
the source say now?*

## What it does

| Method | Type | Purpose |
|---|---|---|
| `pin(url, question, options)` | write | Fetch the source once, extract a label plus a verbatim quote, store it |
| `recheck(pin_id)` | write | Deterministic containment check; consensus only if the quote is gone |
| `close(pin_id)` | write | Owner stops further checks on a pin |
| `get_pin(pin_id)` | view | Full pin record |
| `is_active(pin_id)` | view | True iff status is ACTIVE |
| `count()` | view | Number of pins created |

The caller supplies 2–5 allowed answers, so nothing is stored as free text that two nodes
could read differently.

## How consensus is used

**`pin`** — a custom leader/validator pair (`gl.vm.run_nondet_unsafe`):

- *Leader*: fetch the page, ask the model for one allowed label plus a verbatim quote.
  If the quote is not literally present in its own copy, it raises `QUOTE_NOT_GROUNDED`
  instead of storing a paraphrase.
- *Validator*: fetches its **own** copy of the page, requires the leader's quote to appear
  in it verbatim, then runs its own extraction and requires the same label. A validator
  never trusts `leader_result.calldata` alone.

**`recheck`** — two stages, deliberately:

1. `gl.eq_principle.strict_eq` over a pure string function: is the stored quote still in
   the page? No model call, no tolerance, fully deterministic.
2. Only when the quote is gone: a second consensus block looks for a new grounded answer.
   If none exists, the pin becomes `NOT_FOUND` — never "false".

## Status model

| Status | Reason | Meaning |
|---|---|---|
| `ACTIVE` | `PINNED` / `PRESENT` / `CHANGED` | Evidence is grounded; `version` bumps on `CHANGED` |
| `ACTIVE` | `FETCH_FAILED` | Source unreachable; status deliberately unchanged |
| `NOT_FOUND` | `NOT_FOUND` | No grounded answer now; this is **not** a claim the fact is false |
| `CLOSED` | `CLOSED` | Owner closed the pin; `recheck` reverts |

## Design rules

- **Deterministic first.** The cheap, exact check runs before any model, and its result is
  consensus-checked by strict equality.
- **Grounding over agreement.** A quote must exist in the *validator's* copy of the page.
  Two models agreeing on a quote they both invented is still rejected.
- **Closed answers.** Extraction maps onto the caller's labels via an explicit whitelist;
  anything else is `UNKNOWN`.
- **Bounded everything.** URL <= 400 chars, question 8-240, quote 24-400, page 120-60000
  chars, <= 5000 pins, <= 50 rechecks per pin, one bounded repair attempt.
- **Untrusted input.** Page text is passed inside `<page>` tags with an explicit
  instruction that it is data, not instructions.

## Limitations

- Local tests are **direct mode with mocked web and LLM responses**. Real network
  behavior on Studionet is not yet proven by these tests.
- Quote containment is not semantic. A page that reflows its text mid-transaction can
  legitimately fail the deterministic step; that is treated as `UNSTABLE_SOURCE`, not
  silently accepted.
- `NOT_FOUND` is about grounding, not truth. A fact can be true and still not be
  quotable from the current page.
- No funds, no staking, no slashing: this is an evidence primitive, not a settlement layer.
- Pages behind a login wall, heavy JS, or bot filters will simply fail to ground.

## Usage

    pin_id = contract.pin(
        "https://status.vendor.example/sla",
        "What monthly uptime does the vendor publish?",
        ["99.9", "99.5", "99.0"],
    )
    contract.recheck(pin_id)          # -> "ACTIVE" | "NOT_FOUND"
    contract.get_pin(pin_id)          # -> full record incl. quote and version

## Running the tests

    pip install -r requirements.txt
    python -m pytest tests/direct -q
    genvm-lint check contracts/evidence_pin.py

Covered: paraphrase rejection, label disagreement, leader label outside the allowed set,
deterministic recheck without any LLM mock, version bump on change, `NOT_FOUND`, recovery,
fetch failure, owner-only close.

## Scope

Standalone Intelligent Contract primitive, no frontend, no product flow. Anyone building a
contract that has to cite the web can embed this instead of writing its own evidence logic.
