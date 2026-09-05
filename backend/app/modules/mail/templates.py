TEMPLATES = {
    "interview_invite": (
        "Interview for {job_title}",
        "Hello {candidate_name},\n\n"
        "You are invited to interview for {job_title} on {datetime}.\n"
        "Confirm: {confirm_url}\n",
    ),
    "offer_letter": (
        "Offer: {job_title}",
        "Hello {candidate_name},\n\n"
        "We are pleased to offer you the {job_title} role. Start date: to be confirmed.\n"
        "Accept: {accept_url}\nDecline: {decline_url}\n",
    ),
    "rejection": (
        "Update on {job_title}",
        "Hello {candidate_name},\n\n"
        "Thank you for applying for {job_title}. We will not move forward at this time. "
        "Please apply again for future openings.\n",
    ),
    "generic": ("Message", "{body}"),
}


def render(template_key: str, context: dict) -> tuple[str, str]:
    subj, body = TEMPLATES.get(template_key, TEMPLATES["generic"])
    return subj.format(**context), body.format(**context)
