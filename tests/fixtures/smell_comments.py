"""Fixture: Comments."""


# This function processes the data
# It takes a list of items
# And returns the processed result
# We need this because the old system was broken
# TODO: refactor this later
# NOTE: this is a temporary fix
# HACK: this works but is not ideal
def process(items):
    # initialize the counter
    count = 0
    # loop through items
    for item in items:
        # check if valid
        if item.valid:
            # increment counter
            count += 1
    # return final count
    return count


def clean_function(items):
    return sum(1 for item in items if item.valid)
