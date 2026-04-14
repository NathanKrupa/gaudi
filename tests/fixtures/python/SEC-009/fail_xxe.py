"""Fixture for SEC-009: XML parsing without disabling external entities."""

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import parse, fromstring
import lxml.etree


def parse_user_xml(path: str):
    return ET.parse(path)


def parse_xml_bytes(data: bytes):
    return ET.fromstring(data)


def parse_via_alias(path: str):
    return parse(path)


def parse_string_via_alias(data: str):
    return fromstring(data)


def parse_with_lxml(path: str):
    return lxml.etree.parse(path)


def parse_lxml_string(data: bytes):
    return lxml.etree.fromstring(data)
