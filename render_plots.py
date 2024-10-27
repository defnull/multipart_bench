from multipart_bench.scenarios import SCENARIOS, Result
from multipart_bench.parsers import parser_table
import os.path
import matplotlib.pyplot as plt
import numpy as np

def load_results(scenario, test):
    fname = f"var/{scenario.name_for(test)}.json"
    if os.path.exists(fname):
        return Result.load(fname)

def plot(scenario, names, blocking, non_blocking):

    fig = plt.figure()
    ax1 = fig.add_subplot(2, 1, 1)
    ax1.set_title(f"Non-blockling parsers: Scenario {scenario.name!r}")
    ax2 = fig.add_subplot(2, 1, 2, sharex=ax1)
    ax2.set_title(f"Blocking parsers: Scenario {scenario.name!r}")

    maxval = 0
    for results, ax in ((blocking, ax2),
                         (non_blocking, ax1)):
        named = [(n,r) for n,r in zip(names, results) if r]
        xpos = np.arange(len(named)) 
        values = [r.size / r.min / 1024 / 1024 for n, r in named[::-1]]
        maxval = max(maxval, max(values))
        rects = ax.barh(xpos, values, .8, label=name, tick_label=[n for n,r in named[::-1]])
        ax.bar_label(rects, padding=2, fmt="%.2f")
        ax.set_xlabel('Throughput in MB/s (higher is better)')
        #ax.set_yticks(x, names[::-1])

    ax1.set_xlim(0, maxval* 1.2)

    plt.tight_layout()
    plt.savefig(f"plots/{scenario.name}.png")

if __name__ == "__main__":
    for scenario in SCENARIOS:
        print(scenario.name)

        names = []
        set1 = []
        set2 = []

        for name, (blocking, non_blocking) in parser_table.items():
            names.append(name)
            set1.append(load_results(scenario, blocking) if blocking else None)
            set2.append(load_results(scenario, non_blocking) if non_blocking else None)
        
        plot(scenario, names, set1, set2)

