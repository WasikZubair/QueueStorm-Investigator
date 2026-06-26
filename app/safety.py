import re


SENSITIVE_TERMS = ("PIN", "OTP", "password", "full card number")

UNSAFE_PATTERNS = [
    r"\b(send|share|provide)\s+(your\s+)?(otp|pin|password)\b",
    r"\bfull\s+card\s+number\b",
    r"\bwe\s+will\s+refund\b",
    r"\brefund\s+confirmed\b",
    r"\breversal\s+confirmed\b",
    r"\baccount\s+unblocked\b",
    r"\bmoney\s+recovered\b",
    r"\bcontact\s+this\s+personal\s+number\b",
]


def safety_reminder(language: str | None = None) -> str:
    if language == "bn":
        return "অনুগ্রহ করে কারো সাথে আপনার PIN বা OTP শেয়ার করবেন না।"
    return "Please do not share your PIN or OTP with anyone."


def sanitize_text(
    text: str,
    language: str | None = None,
    append_official_channel: bool = False,
) -> str:
    safe_text = text
    for pattern in UNSAFE_PATTERNS:
        safe_text = re.sub(
            pattern,
            "we will review this through official support channels",
            safe_text,
            flags=re.IGNORECASE,
        )

    if (
        append_official_channel
        and "official support channels" not in safe_text.lower()
        and language != "bn"
    ):
        safe_text = safe_text.rstrip() + " We will contact you through official support channels."

    return safe_text


def sanitize_response_texts(
    agent_summary: str,
    recommended_next_action: str,
    customer_reply: str,
    language: str | None = None,
) -> tuple[str, str, str]:
    agent_summary = sanitize_text(agent_summary, language)
    recommended_next_action = sanitize_text(recommended_next_action, language)
    customer_reply = sanitize_text(customer_reply, language, append_official_channel=True)

    reminder = safety_reminder(language)
    if language == "bn":
        if "OTP" not in customer_reply and "ওটিপি" not in customer_reply:
            customer_reply = customer_reply.rstrip() + " " + reminder
    elif "do not share your PIN or OTP" not in customer_reply:
        customer_reply = customer_reply.rstrip() + " " + reminder

    return agent_summary, recommended_next_action, customer_reply
