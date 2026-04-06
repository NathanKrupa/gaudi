"""Fixture: Fat script — entry point with too much business logic."""

import click


@click.command()
@click.argument("path")
def main(path):
    # This is fine — CLI parsing
    data = load_data(path)

    # Too much business logic for an entry point
    validated = []
    for item in data:
        if item["status"] == "active":
            item["score"] = calculate_score(item)
            if item["score"] > threshold:
                item["tier"] = "premium"
            else:
                item["tier"] = "standard"
            validated.append(item)
    results = aggregate(validated)
    for r in results:
        r["formatted"] = format_result(r)
        r["validated"] = True
    save_results(results)
    print(f"Processed {len(results)} items")


def load_data(path):
    return []


def calculate_score(item):
    return 0


def aggregate(items):
    return items


def format_result(r):
    return str(r)


def save_results(results):
    pass


threshold = 50
