# TTL by complexity level (seconds)
TTL_BY_LEVEL = {
    "easy": 3600,    # 1 hour
    "medium": 1800,  # 30 minutes
    "hard": 300,     # 5 minutes (minimal caching)
}

# Size limits for cache protection
MAX_RESPONSE_SIZE_KB = 128
MAX_EVIDENCE_SIZE_KB = 64

# PII patterns to filter from evidence
PII_PATTERNS = [
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # email
    r'\b\d{10,12}\b',  # phone numbers
    r'\b\d{4}-\d{2}-\d{2}\b',  # dates
]
