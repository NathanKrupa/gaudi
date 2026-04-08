"""Fixture for ARCH-013: a long function that isn't an entry point is out of scope."""


def transform(rows):
    cleaned = [r.strip() for r in rows]
    filtered = [r for r in cleaned if r]
    counts = {}
    for r in filtered:
        counts[r] = counts.get(r, 0) + 1
    sorted_pairs = sorted(counts.items(), key=lambda kv: -kv[1])
    keys = [k for k, _ in sorted_pairs]
    values = [v for _, v in sorted_pairs]
    pairs = list(zip(keys, values))
    out = []
    for p in pairs:
        out.append(f"{p[0]}\t{p[1]}")
    out.append("--end--")
    out.append("--final--")
    return "\n".join(out)
