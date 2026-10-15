def verify_resume_text(
    resume_text: str
) -> dict:
    """
    Prepare extracted resume text as verified source data.

    This service does not generate or modify resume facts.
    It only validates and stores the original extracted text.
    """

    if not isinstance(
        resume_text,
        str
    ):
        raise ValueError(
            "resume_text must be a string"
        )

    cleaned_text = resume_text.strip()

    if not cleaned_text:
        raise ValueError(
            "Resume text cannot be empty"
        )

    return {
        "verified": True,
        "source": "uploaded_resume",
        "resume_text": cleaned_text
    }