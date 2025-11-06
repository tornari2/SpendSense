"""
Mandatory Disclosure Module

Ensures all recommendations include mandatory disclosure text.
"""

# Mandatory disclosure text for education recommendations
EDUCATION_DISCLOSURE_TEXT = (
    "\n\n"
    "This is educational content, not financial advice. "
    "Consult a licensed advisor for personalized guidance."
)

# Mandatory disclosure text for offer recommendations
OFFER_DISCLOSURE_TEXT = (
    "\n\n"
    "This is a third-party offer, not financial advice. "
    "Consult a licensed advisor for personalized guidance."
)


def append_disclosure(content: str, recommendation_type: str = "education") -> str:
    """
    Append mandatory disclosure to recommendation content.
    
    Args:
        content: Original recommendation content
        recommendation_type: Type of recommendation ('education' or 'offer')
    
    Returns:
        Content with disclosure appended
    
    Note:
        If disclosure is already present, it won't be duplicated.
    """
    # Select appropriate disclosure text based on type
    if recommendation_type == "offer":
        disclosure_text = OFFER_DISCLOSURE_TEXT
        # Check for both disclosures to avoid duplicates
        if OFFER_DISCLOSURE_TEXT.strip() in content or EDUCATION_DISCLOSURE_TEXT.strip() in content:
            return content
    else:
        disclosure_text = EDUCATION_DISCLOSURE_TEXT
        # Check for both disclosures to avoid duplicates
        if EDUCATION_DISCLOSURE_TEXT.strip() in content or OFFER_DISCLOSURE_TEXT.strip() in content:
            return content
    
    # Append disclosure
    return content + disclosure_text

