"""Fixture for SMELL-026: comments that narrate what the code used to do."""


def shelve(book, shelf):
    # It used to drop the book when the shelf was full.
    if shelf.full:
        shelf = shelf.overflow
    # Since #412 the overflow shelf takes the book instead.
    shelf.add(book)
    # Previously, we sorted the shelf on every add.
    return shelf


def label(book):
    # The old implementation read the label from the cover.
    return book.spine_label  # we no longer read the cover


# Before PR #87 labels were upper-cased here.
LABEL_CASE = "title"
