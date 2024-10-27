from multipart_bench.scenarios import SCENARIOS, Result
from multipart_bench.parsers import parser_table
from tabulate import tabulate
import os.path

def load_result(scenario, test):
    fname = f"var/{scenario.name_for(test)}.json"
    if os.path.exists(fname):
        return Result.load(fname)

if __name__ == "__main__":
    for scenario in SCENARIOS:
        print(f"### Scenario: {scenario.name}")
        print(scenario.description)
        print()

        head = ["Parser", "Blocking (MB/s)", "Non-Blocking (MB/s)"]
        rows = []
        for name, variants in parser_table.items():
            if not any(variants): continue
            row = [name]
            for variant in variants:
                row += [load_result(scenario, variant) if variant else None]
            rows.append(row)
        
        def format(field, best):
            if not field:
                return "-"
            if field == best:
                return f"{field / 1024 / 1024:.2f} MB/s (100%)"
            return f"{field / 1024 / 1024:.2f} MB/s ({field / (best/100):>.0f}%)"
        
        baseline_blocking = max(row[1].throughput for row in rows if row[0] == "multipart")
        baseline_async    = max(row[2].throughput for row in rows if row[0] == "multipart")
        for row in rows:
            row[1] = format(row[1] and row[1].throughput, baseline_blocking)
            row[2] = format(row[2] and row[2].throughput, baseline_async)

        print(tabulate(rows, headers=head, tablefmt="github"))
        print()
