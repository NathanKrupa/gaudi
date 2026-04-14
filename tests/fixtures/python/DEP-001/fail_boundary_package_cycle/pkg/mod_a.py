# ABOUTME: Imports mod_b via package-style import, creating a cycle.
# ABOUTME: Proves DEP-001 detects cycles through "from pkg import" resolution.
from pkg import mod_b
