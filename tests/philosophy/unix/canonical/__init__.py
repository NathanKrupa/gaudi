"""
Unix / Minimalist reference implementation of the canonical task.

Four independent scripts — ``validate.py``, ``price.py``,
``reserve.py``, ``notify.py`` — each with its own ``main()`` entry
point. Inter-stage communication is JSON-lines on stdin/stdout.
The full pipeline is a shell one-liner:

    cat orders.jsonl \\
        | python -m tests.philosophy.unix.canonical.validate \\
        | python -m tests.philosophy.unix.canonical.price \\
        | python -m tests.philosophy.unix.canonical.reserve \\
        | python -m tests.philosophy.unix.canonical.notify

Zero classes, zero dependencies beyond the Python standard library,
flat directory tree. See ``README.md`` for the full rubric score.
"""
