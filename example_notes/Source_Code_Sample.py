"""Source code sample for WriteOnSide text-file editing."""


def compute_total(values: list[int]) -> int:
    total = 0
    for value in values:
        total += value
    return total


if __name__ == "__main__":
    print(compute_total([1, 2, 3, 4]))

