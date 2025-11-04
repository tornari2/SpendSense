"""
Tone Validation Module

Validates recommendation text to ensure supportive, educational tone
without shaming or judgmental language.
"""

import re
from typing import List, Tuple


# Prohibited language patterns (case-insensitive)
PROHIBITED_PHRASES = [
    # Shaming phrases
    r"you're overspending",
    r"you are overspending",
    r"bad habits",
    r"you should know better",
    r"irresponsible spending",
    r"financial mistakes",
    r"poor financial decisions",
    r"you're wasting money",
    r"you are wasting money",
    r"reckless spending",
    r"careless spending",
    
    # Judgmental phrases
    r"you need to",
    r"you must",
    r"you failed to",
    r"you should have",
    r"you didn't",
    r"you don't",
    r"you can't",
    r"you couldn't",
    r"you haven't",
    
    # Fear-mongering phrases
    r"you'll go bankrupt",
    r"you will go bankrupt",
    r"financial disaster",
    r"ruin your credit",
    r"lose everything",
    r"financial ruin",
    r"going broke",
]


# Compile regex patterns for case-insensitive matching
PROHIBITED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in PROHIBITED_PHRASES
]


def validate_tone(text: str) -> Tuple[bool, List[str]]:
    """
    Validate text tone against prohibited language.
    
    CRITICAL: Must detect and flag any shaming, judgmental, or fear-mongering language.
    Returns violations for operator review.
    
    Args:
        text: Text to validate
    
    Returns:
        Tuple of (is_valid, list_of_violations)
        - is_valid: True if no prohibited language found
        - list_of_violations: List of prohibited phrases found (empty if valid)
    """
    violations = []
    text_lower = text.lower()
    
    # Check each prohibited pattern
    for pattern in PROHIBITED_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            # Get the actual matched text (case-preserved)
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matched_text = match.group(0)
                if matched_text not in violations:
                    violations.append(matched_text)
    
    is_valid = len(violations) == 0
    
    return is_valid, violations


def check_empowering_tone(text: str) -> Tuple[bool, List[str]]:
    """
    Check if text uses empowering, supportive language.
    
    This is a positive check - looks for good patterns rather than just avoiding bad ones.
    
    Args:
        text: Text to check
    
    Returns:
        Tuple of (has_empowering_tone, positive_patterns_found)
        - has_empowering_tone: True if empowering language is present
        - positive_patterns_found: List of positive patterns found
    """
    empowering_patterns = [
        r"you can",
        r"this will help",
        r"consider",
        r"you may want to",
        r"understanding",
        r"learning about",
        r"this can help",
    ]
    
    found_patterns = []
    text_lower = text.lower()
    
    for pattern_str in empowering_patterns:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        if pattern.search(text):
            found_patterns.append(pattern_str)
    
    return len(found_patterns) > 0, found_patterns

