import os.path
import platform
from importlib import metadata

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from multipart_bench.parsers import parser_table
from multipart_bench.scenarios import SCENARIOS, Result


def package_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not installed"


def python_version():
    return platform.python_version()


def load_result(scenario, parser):
    path = f"var/{scenario.name_for(parser)}.json"
    if os.path.exists(path):
        return Result.load(path)


def format_result(result, baseline, available=True):
    if not available:
        return "-"
    if not result:
        return "*failed*"

    throughput = result.throughput
    mbps = throughput / 1024 / 1024
    percent = 100 * throughput / baseline if baseline else 0
    return f"{mbps:.2f} MB/s ({percent:.0f}%)"


def scenario_table(scenario):
    rows = []
    for name, variants in parser_table.items():
        if not any(variants):
            continue
        blocking_variant, sansio_variant = variants
        blocking = load_result(scenario, blocking_variant) if blocking_variant else None
        sansio = load_result(scenario, sansio_variant) if sansio_variant else None
        rows.append(
            {
                "name": name,
                "blocking": blocking,
                "blocking_available": bool(blocking_variant),
                "sansio": sansio,
                "sansio_available": bool(sansio_variant),
            }
        )

    baseline_rows = [row for row in rows if row["name"] == "multipart"]
    baseline_blocking = (
        baseline_rows[0]["blocking"].throughput
        if baseline_rows and baseline_rows[0]["blocking"]
        else None
    )
    baseline_sansio = (
        baseline_rows[0]["sansio"].throughput
        if baseline_rows and baseline_rows[0]["sansio"]
        else None
    )

    return {
        "name": scenario.name,
        "rows": [
            {
                "name": row["name"],
                "blocking": format_result(
                    row["blocking"], baseline_blocking, row["blocking_available"]
                ),
                "sansio": format_result(
                    row["sansio"], baseline_sansio, row["sansio_available"]
                ),
            }
            for row in rows
        ],
    }


def main():
    env = Environment(
        loader=FileSystemLoader("."),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.globals["package_version"] = package_version
    env.globals["python_version"] = python_version
    template = env.get_template("README.md.j2")
    results = {scenario.name: scenario_table(scenario) for scenario in SCENARIOS}

    print(template.render(results=results))


if __name__ == "__main__":
    main()
