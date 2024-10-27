import sys
import cProfile
import time

if __name__ == "__main__":
    #: Run benchmarks in rounds, interleaved with the others, to rule out
    #   low frequency performance changes (e.g. CPU temp throttling) that
    #   would benefit early benchmarks.
    rounds = 10
    #: Allow CPU to cool down between tests
    sleeptime = 1
    #: Continue testing for at least this many seconds per test
    mintime = 10
    #: Continue testing until the best time was not beaten for this many runs
    confidence = 100

    print("Loading scenarios...")
    from multipart_bench.scenarios import SCENARIOS
    from multipart_bench.parsers import parser_table, PARSERS

    print("Preparing benchmarks...")
    alltests = [] # (name, scenario, parser)
    for scenario in SCENARIOS:
        scenario.calibrated = 1000
        for parser in PARSERS:
            name = scenario.name_for(parser)

            # Filter out benchmarks based on command line args
            if sys.argv[1:] and not any(arg in name for arg in sys.argv[1:]):
                continue

            print(f"Seeding {name} ", flush=True)

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

            # Calibarate the number of repeats per scenario so that the slowest
            # parser needs roughly 10ms per test run. This makes fast scenarios
            # more reliable, while slow scenarios still complete in a reasonable
            # amount of time.
            baseline = scenario.run_bench(parser)
            n = int(.01 // baseline)
            if n < scenario.calibrated:
                scenario.calibrated = max(1, n)

            alltests.append((name, scenario, parser))

    print("Running benchmarks ...")
    results = {}
    for round in range(rounds):
        for name, scenario, parser in alltests:
            print(f"{round+1}/{rounds} {name} ", end="", flush=True)

            # Allow CPU to cool down
            time.sleep(sleeptime)
            # Run the actual benchmark
            result = scenario.timeit(parser,
                                     n=scenario.calibrated,
                                     mintime=mintime,
                                     confidence=confidence)
            # Prepend results from last round
            if round > 0:
                result.times[:] = results[name].times + result.times
            # Remember results for next round
            results[name] = result
            # Store results for later processing
            result.save_to(f"var/{name}.json")
            # Print result
            print(f"{result.throughput / 1024 / 1024:.2f}MB/s")
            
