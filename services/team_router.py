TEAM_MAP = {
    'Network': 'Network Support',
    'Hardware': 'Hardware Support',
    'Software': 'Application Support',
    'Access & Account': 'IAM / Access Management',
    'Security': 'Security Operations',
    'Email': 'Email Support',
    'Database': 'Database Support',
    'Other': 'Service Desk / Manual Review'
}


def recommended_team(category):
    return TEAM_MAP.get(category, TEAM_MAP['Other'])
