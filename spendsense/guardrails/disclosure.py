"""
Mandatory Disclosure Module

Ensures all recommendations include mandatory disclosure text.
"""

# Mandatory disclosure text
DISCLOSURE_TEXT = (
    "\n\n"
    "This is educational content, not financial advice. "
    "Consult a licensed advisor for personalized guidance."
)


def append_disclosure(content: str) -> str:
    """
    Append mandatory disclosure to recommendation content.
    
    Args:
        content: Original recommendation content
    
    Returns:
        Content with disclosure appended
    
    Note:
        If disclosure is already present, it won't be duplicated.
    """
    # Check if disclosure is already present
    if DISCLOSURE_TEXT.strip() in content:
        return content
    
    # Append disclosure
    return content + DISCLOSURE_TEXT

