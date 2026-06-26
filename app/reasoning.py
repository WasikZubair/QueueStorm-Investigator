from collections import Counter, defaultdict

from app.schemas import Event, EvidenceItem


RETRY_STATUSES = {"retry", "retried", "retrying"}
FAILURE_STATUSES = {"failed", "failure", "error"}
SUCCESS_STATUSES = {"success", "succeeded", "completed"}


def _normalized_state(event: Event) -> str:
    candidates = [event.status, event.type]
    for value in candidates:
        if value:
            lowered = value.lower()
            if lowered in RETRY_STATUSES:
                return "retry"
            if lowered in FAILURE_STATUSES:
                return "failure"
            if lowered in SUCCESS_STATUSES:
                return "success"
    return "unknown"


def _event_ids(events: list[Event]) -> list[str]:
    return [event.event_id for event in events if event.event_id]


def investigate_events(
    events: list[Event],
) -> tuple[str, str, float, list[str], list[EvidenceItem]]:
    if len(events) < 2:
        return (
            "insufficient_data",
            "Not enough event data to form a reliable preliminary finding.",
            0.2,
            [],
            [],
        )

    evidence: list[EvidenceItem] = []
    transaction_states: dict[str, set[str]] = defaultdict(set)
    transaction_events: dict[str, list[Event]] = defaultdict(list)
    queue_counts: Counter[str] = Counter()
    retry_events: list[Event] = []
    failure_events: list[Event] = []

    for event in events:
        state = _normalized_state(event)
        if event.queue:
            queue_counts[event.queue] += 1
        if event.transaction_id:
            transaction_states[event.transaction_id].add(state)
            transaction_events[event.transaction_id].append(event)
        if state == "retry":
            retry_events.append(event)
        elif state == "failure":
            failure_events.append(event)

    matched_transactions: set[str] = set()

    if len(retry_events) >= 2:
        evidence.append(
            EvidenceItem(
                rule="high_retry_volume",
                detail=f"Detected {len(retry_events)} retry events in the submitted log.",
                event_ids=_event_ids(retry_events),
            )
        )
        matched_transactions.update(
            event.transaction_id for event in retry_events if event.transaction_id
        )

    if len(failure_events) >= 2:
        evidence.append(
            EvidenceItem(
                rule="high_failure_volume",
                detail=f"Detected {len(failure_events)} failure events in the submitted log.",
                event_ids=_event_ids(failure_events),
            )
        )
        matched_transactions.update(
            event.transaction_id for event in failure_events if event.transaction_id
        )

    repeated_queues = [queue for queue, count in queue_counts.items() if count >= 3]
    if repeated_queues:
        evidence.append(
            EvidenceItem(
                rule="repeated_events_from_same_queue",
                detail=(
                    "Multiple events came from the same queue: "
                    + ", ".join(sorted(repeated_queues))
                ),
                event_ids=_event_ids(
                    [event for event in events if event.queue in repeated_queues]
                ),
            )
        )

    inconsistent_transactions = []
    for transaction_id, states in transaction_states.items():
        observed_states = states & {"success", "failure", "retry"}
        if len(observed_states) >= 2 and "success" in observed_states:
            inconsistent_transactions.append(transaction_id)
            matched_transactions.add(transaction_id)

    if inconsistent_transactions:
        related_events = [
            event
            for transaction_id in inconsistent_transactions
            for event in transaction_events[transaction_id]
        ]
        evidence.append(
            EvidenceItem(
                rule="mixed_transaction_states",
                detail=(
                    "Transactions had mixed success/failure/retry states: "
                    + ", ".join(sorted(inconsistent_transactions))
                ),
                event_ids=_event_ids(related_events),
            )
        )

    has_queue_storm_signals = len(retry_events) >= 2 or (
        len(failure_events) >= 2 and bool(repeated_queues)
    )
    if has_queue_storm_signals:
        classification = "queue_storm_likely"
        verdict = "Retry and queue repetition patterns indicate a likely queue storm."
        confidence = 0.82 if len(evidence) >= 2 else 0.7
    elif inconsistent_transactions:
        classification = "transaction_inconsistency"
        verdict = "A transaction shows conflicting lifecycle states and needs review."
        confidence = 0.68
    else:
        classification = "normal_or_low_risk"
        verdict = "No strong retry, failure, queue storm, or transaction inconsistency signals were found."
        confidence = 0.55

    return (
        classification,
        verdict,
        confidence,
        sorted(matched_transactions),
        evidence,
    )
