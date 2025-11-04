"""
Merchant catalog with realistic merchant names and category mappings.
No external JSON needed - embedded as constant for easy access.
"""

# Merchant catalog: name -> (category_primary, merchant_entity_id, typical_channel)
# Simplified categories as per user requirements
MERCHANT_CATALOG = {
    # Food & Dining
    "Starbucks": ("Food and Drink", "merchant_001", "in_store"),
    "McDonald's": ("Food and Drink", "merchant_002", "in_store"),
    "Chipotle": ("Food and Drink", "merchant_003", "in_store"),
    "Panera Bread": ("Food and Drink", "merchant_004", "in_store"),
    "Subway": ("Food and Drink", "merchant_005", "in_store"),
    "Domino's Pizza": ("Food and Drink", "merchant_006", "online"),
    "DoorDash": ("Food and Drink", "merchant_007", "online"),
    "Uber Eats": ("Food and Drink", "merchant_008", "online"),
    "Whole Foods": ("Food and Drink", "merchant_009", "in_store"),
    "Trader Joe's": ("Food and Drink", "merchant_010", "in_store"),
    "Safeway": ("Food and Drink", "merchant_011", "in_store"),
    "Kroger": ("Food and Drink", "merchant_012", "in_store"),
    "Dunkin": ("Food and Drink", "merchant_013", "in_store"),
    
    # Subscriptions & Entertainment
    "Netflix": ("Entertainment", "merchant_014", "online"),
    "Spotify": ("Entertainment", "merchant_015", "online"),
    "Hulu": ("Entertainment", "merchant_016", "online"),
    "Disney+": ("Entertainment", "merchant_017", "online"),
    "HBO Max": ("Entertainment", "merchant_018", "online"),
    "Amazon Prime": ("Entertainment", "merchant_019", "online"),
    "YouTube Premium": ("Entertainment", "merchant_020", "online"),
    "Apple Music": ("Entertainment", "merchant_021", "online"),
    "Audible": ("Entertainment", "merchant_022", "online"),
    "New York Times": ("Entertainment", "merchant_023", "online"),
    "The Athletic": ("Entertainment", "merchant_024", "online"),
    
    # Fitness & Health
    "Planet Fitness": ("Health and Fitness", "merchant_025", "in_store"),
    "LA Fitness": ("Health and Fitness", "merchant_026", "in_store"),
    "Peloton": ("Health and Fitness", "merchant_027", "online"),
    "ClassPass": ("Health and Fitness", "merchant_028", "online"),
    "CVS Pharmacy": ("Health and Fitness", "merchant_029", "in_store"),
    "Walgreens": ("Health and Fitness", "merchant_030", "in_store"),
    
    # Transportation
    "Shell": ("Transportation", "merchant_031", "in_store"),
    "Chevron": ("Transportation", "merchant_032", "in_store"),
    "BP": ("Transportation", "merchant_033", "in_store"),
    "Uber": ("Transportation", "merchant_034", "online"),
    "Lyft": ("Transportation", "merchant_035", "online"),
    
    # Shopping
    "Amazon": ("Shopping", "merchant_036", "online"),
    "Target": ("Shopping", "merchant_037", "in_store"),
    "Walmart": ("Shopping", "merchant_038", "in_store"),
    "Costco": ("Shopping", "merchant_039", "in_store"),
    "Best Buy": ("Shopping", "merchant_040", "in_store"),
    "Home Depot": ("Shopping", "merchant_041", "in_store"),
    "IKEA": ("Shopping", "merchant_042", "in_store"),
    "Macy's": ("Shopping", "merchant_043", "in_store"),
    "Nike": ("Shopping", "merchant_044", "online"),
    "Zara": ("Shopping", "merchant_045", "in_store"),
    
    # Utilities & Services
    "Comcast": ("Utilities", "merchant_046", "online"),
    "AT&T": ("Utilities", "merchant_047", "online"),
    "Verizon": ("Utilities", "merchant_048", "online"),
    "T-Mobile": ("Utilities", "merchant_049", "online"),
    "PG&E": ("Utilities", "merchant_050", "online"),
    "Electric Company": ("Utilities", "merchant_051", "other"),
    "Water Company": ("Utilities", "merchant_052", "other"),
    "Gas Company": ("Utilities", "merchant_053", "other"),
    
    # Insurance
    "State Farm": ("Insurance", "merchant_054", "online"),
    "Geico": ("Insurance", "merchant_055", "online"),
    "Progressive": ("Insurance", "merchant_056", "online"),
    
    # Travel
    "Airbnb": ("Travel", "merchant_057", "online"),
    "Booking.com": ("Travel", "merchant_058", "online"),
    "United Airlines": ("Travel", "merchant_059", "online"),
    "Delta Airlines": ("Travel", "merchant_060", "online"),
    "Hilton": ("Travel", "merchant_061", "online"),
    "Marriott": ("Travel", "merchant_062", "online"),
    
    # Personal Care
    "Sephora": ("Personal Care", "merchant_063", "in_store"),
    "Ulta": ("Personal Care", "merchant_064", "in_store"),
    "Great Clips": ("Personal Care", "merchant_065", "in_store"),
    
    # Pet Care
    "Petco": ("Pet Care", "merchant_066", "in_store"),
    "PetSmart": ("Pet Care", "merchant_067", "in_store"),
    "Chewy": ("Pet Care", "merchant_068", "online"),
    
    # Home Services
    "Rover": ("Services", "merchant_069", "online"),
    "TaskRabbit": ("Services", "merchant_070", "online"),
    
    # Coffee Shops (more variety)
    "Peet's Coffee": ("Food and Drink", "merchant_071", "in_store"),
    "The Coffee Bean": ("Food and Drink", "merchant_072", "in_store"),
    
    # Fast Casual
    "Five Guys": ("Food and Drink", "merchant_073", "in_store"),
    "In-N-Out": ("Food and Drink", "merchant_074", "in_store"),
    "Shake Shack": ("Food and Drink", "merchant_075", "in_store"),
    
    # Cloud Services
    "Dropbox": ("Services", "merchant_076", "online"),
    "Google One": ("Services", "merchant_077", "online"),
    "iCloud": ("Services", "merchant_078", "online"),
    
    # Education
    "Coursera": ("Education", "merchant_079", "online"),
    "Udemy": ("Education", "merchant_080", "online"),
    "LinkedIn Learning": ("Education", "merchant_081", "online"),
    
    # Gaming
    "PlayStation Network": ("Entertainment", "merchant_082", "online"),
    "Xbox Live": ("Entertainment", "merchant_083", "online"),
    "Nintendo Switch Online": ("Entertainment", "merchant_084", "online"),
    "Steam": ("Entertainment", "merchant_085", "online"),
    
    # Specialty Retail
    "REI": ("Shopping", "merchant_086", "in_store"),
    "Dick's Sporting Goods": ("Shopping", "merchant_087", "in_store"),
    "Office Depot": ("Shopping", "merchant_088", "in_store"),
    "Staples": ("Shopping", "merchant_089", "in_store"),
    
    # Dining (More variety)
    "Olive Garden": ("Food and Drink", "merchant_090", "in_store"),
    "Applebee's": ("Food and Drink", "merchant_091", "in_store"),
    "Chili's": ("Food and Drink", "merchant_092", "in_store"),
    "Red Lobster": ("Food and Drink", "merchant_093", "in_store"),
    
    # Convenience
    "7-Eleven": ("Shopping", "merchant_094", "in_store"),
    "Circle K": ("Shopping", "merchant_095", "in_store"),
    
    # Wine & Spirits
    "Total Wine": ("Food and Drink", "merchant_096", "in_store"),
    "BevMo": ("Food and Drink", "merchant_097", "in_store"),
    
    # Home Improvement
    "Lowe's": ("Shopping", "merchant_098", "in_store"),
    "Ace Hardware": ("Shopping", "merchant_099", "in_store"),
    
    # Banking (for fees)
    "Bank Fee": ("Banking", "merchant_100", "other"),
    
    # Income/Payroll merchants
    "Payroll Deposit - Acme Corp": ("Income", "merchant_101", "other"),
    "Direct Deposit - TechCo": ("Income", "merchant_102", "other"),
    "Salary Payment - StartUp Inc": ("Income", "merchant_103", "other"),
    "Payroll ACH - BigCorp": ("Income", "merchant_104", "other"),
    "Deposit - Freelance Client": ("Income", "merchant_105", "other"),
    "Paycheck - Enterprise LLC": ("Income", "merchant_106", "other"),
    "Income - Consulting": ("Income", "merchant_107", "other"),
    "Wages - Local Business": ("Income", "merchant_108", "other"),
}

# Payroll/Income merchant patterns (for backward compatibility)
INCOME_MERCHANTS = [
    "Payroll Deposit - Acme Corp",
    "Direct Deposit - TechCo",
    "Salary Payment - StartUp Inc",
    "Payroll ACH - BigCorp",
    "Deposit - Freelance Client",
    "Paycheck - Enterprise LLC",
    "Income - Consulting",
    "Wages - Local Business",
]


def get_merchant_info(merchant_name):
    """Get category and entity ID for a merchant."""
    if merchant_name in MERCHANT_CATALOG:
        category, entity_id, channel = MERCHANT_CATALOG[merchant_name]
        return {
            "category_primary": category,
            "merchant_entity_id": entity_id,
            "payment_channel": channel
        }
    return None


def get_all_merchants():
    """Get list of all merchant names."""
    return list(MERCHANT_CATALOG.keys())


def get_merchants_by_category(category):
    """Get all merchants in a specific category."""
    return [
        name for name, (cat, _, _) in MERCHANT_CATALOG.items()
        if cat == category
    ]


def get_subscription_merchants():
    """Get merchants that are typically subscriptions."""
    subscription_categories = ["Entertainment", "Health and Fitness", "Services", "Education"]
    subscriptions = []
    for name, (cat, _, _) in MERCHANT_CATALOG.items():
        if cat in subscription_categories:
            subscriptions.append(name)
    return subscriptions


def is_subscription_likely(merchant_name):
    """Check if a merchant is likely to be a subscription."""
    return merchant_name in get_subscription_merchants()


def get_income_merchants():
    """Get all income/payroll merchant names."""
    return INCOME_MERCHANTS

