from multipart_bench.scenarios import SCENARIOS
from multipart_bench.parsers import parser_table
from tabulate import tabulate
import sys

if __name__ == "__main__":
    bench_args = dict(mintime=60, minrepeat=100, confidence=20)

    for scenario in SCENARIOS:
        if sys.argv[1:] and scenario.name not in sys.argv[1:]:
            continue
        print(f"### Scenario: {scenario.name}")
        print(scenario.description)
        print()

        head = ["Parser", "Blocking (MB/s)", "Non-Blocking (MB/s)"]
        rows = []
        best = 0
        for name, variants in parser_table.items():
            row = [name]
            for variant in variants:
                if not variant:
                    row.append(-1)
                else:
                    result = scenario.timeit(variant, **bench_args)
                    row += [result.throughput]
                    best = max(best, result.throughput)
            rows.append(row)

        def format(field, best):
            if field < 0:
                return "-"
            if field == best:
                return f"{field / 1024 / 1024:.2f} MB/s (100%)"
            return f"{field / 1024 / 1024:.2f} MB/s ({field / (best/100):>.0f}%)"

        best_blocking = max(row[1] for row in rows)
        best_async    = max(row[2] for row in rows)
        for row in rows:
            row[1] = format(row[1], best_blocking)
            row[2] = format(row[2], best_async)

        print(tabulate(rows, headers=head, tablefmt="github"))
        print()
