import re

RULES = {
    'Critical': ['server down', 'complete outage', 'security breach', 'ransomware', 'data loss', 'production down', 'all users affected', 'possible ransomware'],
    'High': ['cannot login', 'can not login', 'vpn unavailable', 'vpn is not connecting', 'email unavailable', 'application unavailable', 'network outage', 'unable to login'],
    'Medium': ['software error', 'printer issue', 'slow system', 'application bug', 'error message', 'not working'],
    'Low': ['password reset', 'software installation', 'general question', 'minor configuration', 'how do i', 'request access']
}


def detect_priority(text):
    normalized = re.sub(r'[^a-z0-9 ]', ' ', text.lower())
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    for priority in ('Critical', 'High', 'Medium', 'Low'):
        matches = [phrase for phrase in RULES[priority] if phrase in normalized]
        if matches:
            return priority, f"Matched {priority.lower()} priority keyword(s): {', '.join(matches)}", matches
    return 'Medium', 'No critical rule matched; defaulting to Medium for manual triage.', []
