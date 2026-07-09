import argparse
from fnmatch import fnmatch
import random
import sys
import cProfile
import time
import gc
import typing

PROFILES = {
    "fast": {"confidence_level": 0.80, "precision": 0.05, "rounds": 3},
    "default": {"confidence_level": 0.95, "precision": 0.02, "rounds": 5},
    "slow": {"confidence_level": 0.95, "precision": 0.01, "rounds": 10},
    "slower": {"confidence_level": 0.98, "precision": 0.005, "rounds": 15},
    "slowest": {"confidence_level": 0.99, "precision": 0.0025, "rounds": 20},
}

ap = argparse.ArgumentParser()
ap.add_argument(
    "-p",
    "--profile",
    default="default",
    choices=PROFILES,
    help="Benchmark stability profile: fast, default, slow, slower, or slowest",
)
ap.add_argument(
    "-t",
    "--mintime",
    default=1,
    type=float,
    help="Continue testing for at least this many seconds per test",
)
ap.add_argument(
    "-r",
    "--rounds",
    default=None,
    type=int,
    help="Minimum number of times to repeat the entire benchmark",
)
ap.add_argument(
    "--append",
    action="store_true",
    help="Append results to previous run instead of replacing results.",
)
ap.add_argument(
    "--list",
    action="store_true",
    help="List all benchmark names instead of running them.",
)
ap.add_argument(
    "--sleep",
    default=0.1,
    type=int,
    help="Seconds to wait between tests to allow CPUs to cool down.",
)

ap.add_argument(
    "benchmarks", nargs="*", default="*", help="Glob patterns for benchmarks to run"
)


def shuffle(values):
    values = list(values)
    random.shuffle(values)
    return values


if __name__ == "__main__":
    args = ap.parse_args()
    #: Allow CPU to cool down between tests
    sleeptime = args.sleep
    #: Continue testing for at least this many seconds per test
    mintime = args.mintime
    #: Confidence interval and precision for the selected stability profile
    profile = PROFILES[args.profile]
    confidence_level = profile["confidence_level"]
    precision = profile["precision"]
    rounds = args.rounds if args.rounds is not None else profile["rounds"]

    from multipart_bench.scenarios import SCENARIOS, Result, Scenario
    from multipart_bench.parsers import PARSERS, dummy_parser

    if args.list:
        for scenario in SCENARIOS:
            for parser in PARSERS:
                name = scenario.name_for(parser)
                if not any(fnmatch(name, glob) for glob in args.benchmarks):
                    continue
                print(name)
        sys.exit(0)

    print("Preparing benchmarks...")
    alltests: list[
        tuple[str, Scenario, typing.Callable[[Scenario], Result]]
    ] = []  # (name, scenario, parser)

    baseline = PARSERS[0]
    calibrated_n = {}

    # Collecting and calibrating benchmarks (scenarios x parsers)
    for scenario in shuffle(SCENARIOS):
        for parser in shuffle(PARSERS):
            name = scenario.name_for(parser)

            if not any(fnmatch(name, glob) for glob in args.benchmarks):
                continue

            # Create profiles for each benchmark and skip failing benchmarks
            pr = cProfile.Profile(timer=time.perf_counter)
            pr.enable()
            try:
                scenario.run_once(parser)
                pr.disable()
                pr.dump_stats(f"var/{name}.prof")
            except Exception as e:
                pr.disable()
                print(f"Skipping {name}: {e}")
                continue

            # Calibarate the number of repeats per test so that each test needs roughly
            # the same time to complete. This makes fast tests more stable, while slow
            # tests still complete in a reasonable amount of time.
            gc.collect()
            target_time = 1.0
            min_n = 10
            result = scenario.run_bench(parser, n=min_n, null_func=dummy_parser) * min_n
            calibrated_n[name] = n = max(min_n, int(target_time // result))

            print(f"Seeded {name} (n={n}) ", flush=True)

            alltests.append((name, scenario, parser))

    print(
        f"Running benchmarks ({args.profile}: {rounds} min rounds, {confidence_level:.0%} confidence level, ±{precision:.2%} precision) ..."
    )
    results: dict[str, Result] = {}
    confidence_reached = set()
    round = 0
    while round < rounds or any(name not in confidence_reached for name in results):
        print()
        print(
            f"Round {round + 1}/{rounds}: Skipping {len(confidence_reached)}/{len(alltests)} stable tests"
        )
        for name, scenario, parser in shuffle(alltests):
            if name in confidence_reached:
                continue

            print(f"{round + 1}/{rounds} {name} ", end="", flush=True)
            rfname = f"var/{name}.json"

            # Load previous results in append mode
            if args.append and name not in results:
                try:
                    results[name] = Result.load(rfname)
                except FileNotFoundError:
                    pass

            if name not in results:
                results[name] = Result(name, scenario.size, [])

            result = results[name]

            # Allow CPU to cool down
            time.sleep(sleeptime)

            # Run the actual benchmark
            measurement = scenario.run_bench(
                parser, n=calibrated_n[name], null_func=dummy_parser
            )
            result.times.append(measurement)

            # Store results for later processing
            result.save_to(rfname)

            # Mark test as 'good enough' after min-rounds
            if (
                round + 1 >= rounds
                and name not in confidence_reached
                and result.relative_confidence_interval(confidence_level) <= precision
            ):
                confidence_reached.add(name)

            # Print result
            if baseline is parser or round == 0:
                print(
                    f"{result.throughput / 1024 / 1024:.2f}MB/s (±{result.relative_confidence_interval(confidence_level):.2%}, n={calibrated_n[name]})"
                )
            else:
                bsresult = results[scenario.name_for(baseline)]
                percent = 100 * (
                    (result.throughput - bsresult.throughput) / bsresult.throughput
                )
                print(
                    f"{result.throughput / 1024 / 1024:.2f}MB/s ({percent:+.2f}%, ±{result.relative_confidence_interval(confidence_level):.2%}, n={calibrated_n[name]})"
                )

        round += 1
