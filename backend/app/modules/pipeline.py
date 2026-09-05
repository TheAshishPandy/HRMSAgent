class IllegalTransition(Exception):
    def __init__(self, code: str = "illegal_transition", message: str = "Illegal status transition"):
        self.code = code
        self.message = message
        super().__init__(message)


ALLOWED = {
    ("applied", "screened"),
    ("applied", "rejected"),
    ("applied", "withdrawn"),
    ("screened", "interview"),
    ("screened", "rejected"),
    ("screened", "withdrawn"),
    ("interview", "offer"),
    ("interview", "rejected"),
    ("interview", "withdrawn"),
    ("offer", "hired"),
    ("offer", "rejected"),
    ("offer", "withdrawn"),
}


def transition(
    current: str,
    new_status: str,
    *,
    has_feedback: bool = False,
    has_interview: bool = False,
) -> None:
    if current == new_status:
        return
    if (current, new_status) not in ALLOWED:
        raise IllegalTransition()
    if new_status == "offer":
        if not has_interview or not has_feedback:
            raise IllegalTransition("offer_requires_feedback", "Offer requires an interview and feedback")
    if new_status == "rejected" and current == "interview" and not has_feedback:
        raise IllegalTransition("reject_requires_feedback", "Post-interview rejection requires feedback")
    if new_status == "interview" and not has_interview:
        raise IllegalTransition("interview_required", "Interview status requires an interview row")
