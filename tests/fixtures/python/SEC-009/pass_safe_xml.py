"""Passing fixture for SEC-009: defusedxml and hardened lxml parsers."""

import defusedxml.ElementTree as DET
import lxml.etree


def parse_with_defusedxml(path: str):
    return DET.parse(path)


def parse_string_with_defusedxml(data: bytes):
    return DET.fromstring(data)


def parse_lxml_hardened(path: str):
    parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
    return lxml.etree.parse(path, parser=parser)


def parse_lxml_string_hardened(data: bytes):
    parser = lxml.etree.XMLParser(resolve_entities=False, no_network=True)
    return lxml.etree.fromstring(data, parser=parser)
