"""Fixture for SMELL-025: 'new' as a domain word, not a temporal marker.

`new` here means "the issues not previously seen" -- a set-difference result,
the ordinary English sense. Renaming it would make the code worse. The
temporal sense the rule targets is `new_billing_handler` standing beside an
older `billing_handler`.
"""


def triage(issues, ruled):
    new = tuple(issue for issue in issues if issue not in ruled)
    new_items = [i for i in issues if i not in ruled]
    new_count = len(new_items)
    return new, new_items, new_count
