# ABOUTME: Imports only stdlib modules — must not produce a circular-import finding.
# ABOUTME: Proves DEP-001 correctly filters stdlib from the dependency graph.
import os
import sys
import json

x = 1
