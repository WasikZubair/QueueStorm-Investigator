from __future__ import annotations

import re
from datetime import datetime

from app.safety import sanitize_response_texts
from app.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse, Transaction


DEPARTMENT_BY_CASE = {
    "wrong_transfer": "dispute_resolution",
    "payment_failed": "payments_ops",
    "refund_request": "customer_support",
    "duplicate_payment": "payments_ops",
    "merchant_settlement_delay": "merchant_operations",
    "agent_cash_in_issue": "agent_operations",
    "phishing_or_social_engineering": "fraud_risk",
    "other": "customer_support",
}

CASE_TYPE_COMPATIBILITY = {
    "wrong_transfer": {"transfer"},
    "payment_failed": {"payment"},
    "refund_request": {"payment", "refund"},
    "duplicate_payment": {"payment"},
    "merchant_settlement_delay": {"settlement"},
    "agent_cash_in_issue": {"cash_in"},
    "phishing_or_social_engineering": set(),
    "other": {"transfer", "payment", "cash_in", "cash_out", "settlement", "refund"},
}

STATUS_COMPATIBILITY = {
    "wrong_transfer": {"completed"},
    "payment_failed": {"failed", "pending"},
    "refund_request": {"completed", "pending"},
    "duplicate_payment": {"completed"},
    "merchant_settlement_delay": {"pending"},
    "agent_cash_in_issue": {"pending", "failed"},
}

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def analyze_ticket(request: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    complaint = request.complaint.strip()
    normalized = _normalize_text(complaint)
    amounts = _extract_amounts(normalized)
    case_type = _classify_case(normalized, request)
    duplicate_txn = _find_duplicate_payment(request.transaction_history)
    relevant = _match_transaction(case_type, request.transaction_history, normalized, amounts)

    reason_codes = [case_type]
    if duplicate_txn and case_type == "duplicate_payment":
        relevant = duplicate_txn
        reason_codes.append("biller_verification_required")

    verdict = _evidence_verdict(case_type, relevant, request.transaction_history, amounts)
    if case_type == "wrong_transfer" and relevant and _has_established_recipient(relevant, request.transaction_history):
        verdict = "inconsistent"
        reason_codes.extend(["established_recipient_pattern", "evidence_inconsistent"])
    elif verdict == "consistent":
        reason_codes.append("transaction_match")
    elif verdict == "insufficient_data":
        reason_codes.append("needs_clarification")
    else:
        reason_codes.append("evidence_inconsistent")

    severity = _severity(case_type, verdict, relevant, normalized)
    department = DEPARTMENT_BY_CASE[case_type]
    human_review_required = _needs_human_review(case_type, severity, verdict, relevant)
    confidence = _confidence(case_type, verdict, relevant, request.transaction_history)

    agent_summary, recommended_next_action, customer_reply = _build_texts(
        request=request,
        case_type=case_type,
        verdict=verdict,
        severity=severity,
        relevant=relevant,
    )
    agent_summary, recommended_next_action, customer_reply = sanitize_response_texts(
        agent_summary,
        recommended_next_action,
        customer_reply,
        request.language,
    )

    return AnalyzeTicketResponse(
        ticket_id=request.ticket_id,
        relevant_transaction_id=relevant.transaction_id if relevant else None,
        evidence_verdict=verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        agent_summary=agent_summary,
        recommended_next_action=recommended_next_action,
        customer_reply=customer_reply,
        human_review_required=human_review_required,
        confidence=confidence,
        reason_codes=_dedupe(reason_codes),
    )


def _normalize_text(text: str) -> str:
    return text.translate(BN_DIGITS).lower()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_amounts(text: str) -> list[float]:
    amounts = []
    for match in re.finditer(r"(?<![\w+-])\d{2,7}(?:\.\d+)?(?![\w-])", text):
        value = match.group(0)
        if value.startswith("880") or value.startswith("01"):
            continue
        amounts.append(float(value))
    return amounts


def _classify_case(text: str, request: AnalyzeTicketRequest) -> str:
    if _contains_any(text, ("otp", "pin", "password", "suspicious call", "suspicious sms", "sms link", "blocked if", "block threat", "scam", "fraud", "ওটিপি", "পিন", "পাসওয়ার্ড")):
        return "phishing_or_social_engineering"
    if _contains_any(text, ("deducted twice", "paid twice", "double charge", "twice", "duplicate", "duibar", "দুইবার", "ডাবল")):
        return "duplicate_payment"
    if _contains_any(text, ("agent cash in", "cash in", "cash-in", "balance not added", "agent", "এজেন্ট", "ক্যাশ ইন", "ব্যালেন্সে টাকা আসেনি")):
        return "agent_cash_in_issue"
    if _contains_any(text, ("failed", "deducted", "balance deducted", "app showed failed", "কেটে", "কেটে গেছে", "failed hoyeche", "fail hoise", "fail korse", "payment fail")):
        return "payment_failed"
    if _contains_any(text, ("refund", "return money", "changed my mind", "ফেরত")):
        return "refund_request"
    if _contains_any(text, ("merchant settlement", "sales not settled", "settlement", "settled to my account", "মার্চেন্ট সেটেলমেন্ট", "সেটেলমেন্ট আসেনি")) or request.user_type == "merchant":
        return "merchant_settlement_delay"
    if _contains_any(text, ("wrong number", "wrong person", "sent by mistake", "wrong recipient", "reverse it", "brother", "didn't get it", "did not get it", "bhul number", "bhul namber", "vul number", "wrong transfer", "ভুল নম্বর", "ভুল নাম্বার", "ভুল করে")):
        return "wrong_transfer"
    return "other"


def _match_transaction(
    case_type: str,
    transactions: list[Transaction],
    complaint: str,
    amounts: list[float],
) -> Transaction | None:
    if not transactions or case_type == "phishing_or_social_engineering":
        return None

    scored: list[tuple[int, Transaction]] = []
    for txn in transactions:
        score = 0
        has_amount_match = txn.amount is not None and any(
            abs(txn.amount - amount) < 0.01 for amount in amounts
        )
        if amounts and not has_amount_match:
            scored.append((0, txn))
            continue
        if has_amount_match:
            score += 4
        if txn.type in CASE_TYPE_COMPATIBILITY.get(case_type, set()):
            score += 3
        if txn.status in STATUS_COMPATIBILITY.get(case_type, set()):
            score += 2
        if txn.counterparty and txn.counterparty.lower() in complaint:
            score += 3
        if txn.transaction_id and txn.transaction_id.lower() in complaint:
            score += 5
        if _mentions_date_or_time(complaint) and txn.timestamp:
            score += 1
        scored.append((score, txn))

    scored.sort(key=lambda item: (item[0], _timestamp_sort_key(item[1])), reverse=True)
    best_score, best_txn = scored[0]
    if best_score < 4:
        return None

    top_matches = [txn for score, txn in scored if score == best_score]
    if len(top_matches) > 1:
        return None
    return best_txn


def _find_duplicate_payment(transactions: list[Transaction]) -> Transaction | None:
    completed_payments = [
        txn
        for txn in transactions
        if txn.type == "payment" and txn.status == "completed" and txn.amount is not None
    ]
    groups: dict[tuple[float, str | None], list[Transaction]] = {}
    for txn in completed_payments:
        groups.setdefault((txn.amount or 0, txn.counterparty), []).append(txn)

    duplicate_group = max(groups.values(), key=len, default=[])
    if len(duplicate_group) < 2:
        return None
    return sorted(duplicate_group, key=_timestamp_sort_key)[-1]


def _evidence_verdict(
    case_type: str,
    relevant: Transaction | None,
    transactions: list[Transaction],
    amounts: list[float],
) -> str:
    if case_type == "phishing_or_social_engineering":
        return "insufficient_data"
    if not transactions:
        return "insufficient_data"
    if relevant is None:
        plausible_amount_matches = [
            txn
            for txn in transactions
            if txn.amount is not None
            and any(abs(txn.amount - amount) < 0.01 for amount in amounts)
        ]
        if len(plausible_amount_matches) > 1:
            return "insufficient_data"
        if amounts and transactions:
            return "inconsistent"
        return "insufficient_data"
    if case_type == "payment_failed":
        return "consistent" if relevant.status in {"failed", "pending"} else "inconsistent"
    if case_type == "wrong_transfer":
        return "consistent" if relevant.type == "transfer" and relevant.status == "completed" else "inconsistent"
    if case_type == "refund_request":
        return "consistent" if relevant.status in {"completed", "pending"} else "inconsistent"
    if case_type == "duplicate_payment":
        return "consistent" if _find_duplicate_payment(transactions) else "insufficient_data"
    if case_type == "merchant_settlement_delay":
        return "consistent" if relevant.type == "settlement" and relevant.status == "pending" else "inconsistent"
    if case_type == "agent_cash_in_issue":
        return "consistent" if relevant.type == "cash_in" and relevant.status in {"pending", "failed"} else "inconsistent"
    return "insufficient_data" if relevant is None else "consistent"


def _has_established_recipient(relevant: Transaction, transactions: list[Transaction]) -> bool:
    if relevant.type != "transfer" or not relevant.counterparty:
        return False
    same_counterparty = [
        txn for txn in transactions if txn.type == "transfer" and txn.counterparty == relevant.counterparty
    ]
    return len(same_counterparty) >= 3


def _severity(case_type: str, verdict: str, relevant: Transaction | None, complaint: str) -> str:
    if case_type == "phishing_or_social_engineering":
        return "critical"
    if case_type in {"wrong_transfer", "duplicate_payment"}:
        return "medium" if verdict == "inconsistent" or relevant is None else "high"
    if case_type == "payment_failed":
        return "high" if _contains_any(complaint, ("deducted", "কেটে", "balance deducted")) else "medium"
    if case_type == "agent_cash_in_issue":
        return "high" if relevant and relevant.status == "pending" else "medium"
    if case_type == "merchant_settlement_delay":
        return "medium"
    if case_type == "refund_request":
        return "low"
    return "low"


def _needs_human_review(case_type: str, severity: str, verdict: str, relevant: Transaction | None) -> bool:
    if case_type in {"wrong_transfer", "phishing_or_social_engineering", "duplicate_payment"}:
        return True if relevant is not None or case_type != "wrong_transfer" else False
    if case_type == "agent_cash_in_issue" and relevant and relevant.status == "pending":
        return True
    if case_type in {"payment_failed", "merchant_settlement_delay"} and verdict == "consistent":
        return False
    if severity in {"high", "critical"}:
        return True
    if verdict == "inconsistent":
        return True
    return False


def _confidence(
    case_type: str,
    verdict: str,
    relevant: Transaction | None,
    transactions: list[Transaction],
) -> float:
    if case_type == "phishing_or_social_engineering":
        return 0.95
    if verdict == "consistent" and relevant:
        return 0.9
    if verdict == "inconsistent" and relevant:
        return 0.75
    if transactions:
        return 0.65
    return 0.55


def _build_texts(
    request: AnalyzeTicketRequest,
    case_type: str,
    verdict: str,
    severity: str,
    relevant: Transaction | None,
) -> tuple[str, str, str]:
    txn_id = relevant.transaction_id if relevant and relevant.transaction_id else "the reported transaction"
    amount = f"{relevant.amount:g} BDT" if relevant and relevant.amount is not None else "the reported amount"
    counterparty = f" with {relevant.counterparty}" if relevant and relevant.counterparty else ""

    if case_type == "phishing_or_social_engineering":
        return (
            "Customer reports a possible phishing or social engineering attempt involving sensitive credentials.",
            "Escalate to fraud_risk and remind the customer that official support never asks for PIN, OTP, or password.",
            "Thank you for reaching out. We never ask for your PIN, OTP, or password under any circumstances. Our fraud team will review this through official support channels.",
        )
    if case_type == "wrong_transfer":
        return (
            f"Customer reports a possible wrong transfer for {amount} via {txn_id}{counterparty}. Evidence verdict is {verdict}.",
            f"Verify {txn_id} details with the customer before starting or continuing the wrong-transfer dispute workflow.",
            f"We have noted your concern about transaction {txn_id}. Our dispute team will review the case and contact you through official support channels.",
        )
    if case_type == "payment_failed":
        return (
            f"Customer reports a failed payment with possible balance deduction for {amount} via {txn_id}.",
            f"Check {txn_id} ledger status and initiate standard reversal flow only if eligibility is confirmed.",
            f"We have noted your concern about transaction {txn_id}. Our payments team will review it and any eligible amount will be returned through official channels.",
        )
    if case_type == "refund_request":
        return (
            f"Customer requests a refund for {amount} via {txn_id}.",
            "Explain that refund eligibility depends on policy or merchant confirmation and guide the customer through official support.",
            "Thank you for reaching out. Refund eligibility depends on the applicable policy or merchant confirmation. Our team can guide you through the official process.",
        )
    if case_type == "duplicate_payment":
        return (
            f"Customer reports a duplicate payment; {txn_id} appears to be the likely duplicate transaction.",
            f"Verify {txn_id} with payments_ops and the biller before any reversal action.",
            f"We have noted the possible duplicate payment for transaction {txn_id}. Our payments team will verify it and any eligible amount will be returned through official channels.",
        )
    if case_type == "merchant_settlement_delay":
        return (
            f"Merchant reports delayed settlement for {amount} via {txn_id}.",
            "Route to merchant_operations to verify settlement batch status and provide an official update.",
            f"We have noted your concern about settlement {txn_id}. Our merchant operations team will check the batch status and update you through official channels.",
        )
    if case_type == "agent_cash_in_issue":
        if request.language == "bn":
            return (
                f"Customer reports cash-in not reflected for {amount} via {txn_id}.",
                f"Investigate {txn_id} pending cash-in status with agent_operations.",
                f"আপনার লেনদেন {txn_id} এর বিষয়টি আমরা পেয়েছি। আমাদের এজেন্ট অপারেশনস দল এটি যাচাই করবে এবং অফিসিয়াল চ্যানেলে জানাবে।",
            )
        return (
            f"Customer reports agent cash-in not reflected for {amount} via {txn_id}.",
            f"Investigate {txn_id} cash-in status with agent_operations and confirm settlement state.",
            f"We have noted your concern about cash-in transaction {txn_id}. Our agent operations team will review it through official channels.",
        )

    return (
        "Customer provided a general or unclear support complaint with insufficient detail for a specific case type.",
        "Ask for transaction ID, amount, approximate time, and a short description of what went wrong.",
        "Thank you for reaching out. Please share the transaction ID, amount, approximate time, and what went wrong so we can help through official support channels.",
    )


def _mentions_date_or_time(text: str) -> bool:
    return _contains_any(text, ("today", "yesterday", "am", "pm", "সকাল", "বিকাল", "গতকাল"))


def _timestamp_sort_key(txn: Transaction) -> datetime:
    if not txn.timestamp:
        return datetime.min
    try:
        return datetime.fromisoformat(txn.timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.min


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
