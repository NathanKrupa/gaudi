"""Fixture for ARCH-011: a connector branching on parsed XML shape.

The branch inspects the parsed response (an XPath hit, an element tag) to
choose how to translate it. That is format translation, the connector's job —
not a business decision — so ARCH-011 must not fire.
"""

import xml.etree.ElementTree as ET


def parse_grant(payload: str) -> dict:
    root = ET.fromstring(payload)
    if root.find("OpportunityID") is not None:
        return {"id": root.findtext("OpportunityID")}
    else:
        return {"id": root.findtext("FundingOpportunityNumber")}


def classify(element) -> str:
    if element.tag == "Grant":
        return "grant"
    else:
        return "other"
