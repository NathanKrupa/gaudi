"""Fixture for SMELL-026: comments about runtime state and provenance are not history."""


def shelve(book, shelf):
    # The key used to look up the shelf is the branch code.
    key = shelf.branch_code
    # Skip shelves that no longer have room; a full shelf is used to signal overflow.
    if shelf.full:
        return None
    # Reuse the previously fetched index rather than reading it again.
    index = shelf.cached_index
    # Shelving rules: see #412 and docs/shelving.md.
    index.add(key, book)  # (#87)
    # Rows written before #87 carry no shelf label; the index file is rewritten
    # on every add and was rewritten by the last call.
    return index


def renew(loan):
    """Renew the loan if it is not overdue; the old due date is replaced."""
    return loan.extend()


# As noted previously, the index is per branch. A shelf code is originally, and
# always, the branch code plus a number.
SHELF_CODE_FORMAT = "{branch}-{number}"
