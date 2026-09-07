class IllegalTransition(Exception):
    def __init__(self, code: str = "illegal_transition", message: str = "Illegal status transition"):
        self.code = code
        self.message = message
        super().__init__(message)


STAGES = (
    "applied",
    "screened",
    "shortlist",
    "interview",
    "technical",
    "hr_round",
    "offer",
    "hired",
    "rejected",
    "withdrawn",
)

ALLOWED = {
    ("applied", "screened"),
    ("applied", "rejected"),
    ("applied", "withdrawn"),
    ("screened", "shortlist"),
    ("screened", "interview"),
    ("screened", "rejected"),
    ("screened", "withdrawn"),
    ("shortlist", "interview"),
    ("shortlist", "technical"),
    ("shortlist", "rejected"),
    ("shortlist", "withdrawn"),
    ("interview", "technical"),
    ("interview", "hr_round"),
    ("interview", "offer"),
    ("interview", "rejected"),
    ("interview", "withdrawn"),
    ("technical", "hr_round"),
    ("technical", "offer"),
    ("technical", "rejected"),
    ("technical", "withdrawn"),
    ("hr_round", "offer"),
    ("hr_round", "rejected"),
    ("hr_round", "withdrawn"),
    ("offer", "hired"),
    ("offer", "rejected"),
    ("offer", "withdrawn"),
}

INTERVIEW_REQUIRED = {"interview", "technical", "hr_round"}


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
    if new_status == "rejected" and current in INTERVIEW_REQUIRED and not has_feedback:
        raise IllegalTransition("reject_requires_feedback", "Post-interview rejection requires feedback")
    if new_status in INTERVIEW_REQUIRED and not has_interview:
        raise IllegalTransition("interview_required", "Interview status requires an interview row")
