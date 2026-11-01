"""Fixture for SMELL-026: one history-telling phrase per comment."""

# This was previously read from the environment.
SHELF_LIMIT = 40
# The column was renamed from shelf_no.
SHELF_COLUMN = "shelf_code"
# The overflow flag is no longer needed by the scanner.
OVERFLOW = False
# Formerly the branch table held the hours.
HOURS_TABLE = "opening_hours"
# Originally, labels were printed in batches.
LABEL_BATCH = 1
# The scanner was originally a cron job.
SCANNER = "worker"
