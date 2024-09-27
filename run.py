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

        for name, [blocking, non_blocking] in parser_table.items():
            row = [name]
            result = scenario.timeit(blocking, **bench_args)
            row += [f"{result.throughput / 1024 / 1024:.2f} MB/s"]
            if non_blocking:
                result = scenario.timeit(non_blocking, **bench_args)
                row += [f"{result.throughput / 1024 / 1024:.2f} MB/s"]
            else:
                row += ["-"]
            rows.append(row)

        print(tabulate(rows, headers=head, tablefmt="github"))
        print()
