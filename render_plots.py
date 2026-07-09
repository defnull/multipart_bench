from multipart_bench.scenarios import SCENARIOS, Result
from multipart_bench.parsers import parser_table
import os.path
import matplotlib.pyplot as plt
import numpy as np

def load_results(scenario, test):
    fname = f"var/{scenario.name_for(test)}.json"
    if os.path.exists(fname):
        return Result.load(fname)

def parser_status(scenario, test):
    if not test:
        return None, "no result"

    result = load_results(scenario, test)
    if not result:
        return None, "failed"

    return result, None


def throughput(result):
    if not result:
        return 0
    return result.throughput / 1024 / 1024


def plot_one(entries, title, plot_max, output_file):
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    ax.set_title(title)

    ordered = entries[::-1]
    xpos = np.arange(len(ordered))
    values = [throughput(result) for _, result, _ in ordered]
    rects = ax.barh(xpos, values, .8, tick_label=[name for name, _, _ in ordered])

    for rect, (_, result, status), value in zip(rects, ordered, values):
        y = rect.get_y() + rect.get_height() / 2
        if result:
            ax.text(value + plot_max * 0.01, y, f"{value:.2f} MB/s", va="center", ha="left")
        else:
            color = "red" if status == "failed" else "dimgray"
            ax.text(plot_max * 0.02, y, status, va="center", ha="left", color=color)

    ax.set_xlabel('Throughput in MB/s (higher is better)')
    ax.set_xlim(0, plot_max)
    ax.set_ylim(-0.5, len(ordered) - 0.5)

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close(fig)

def plot_one_horizontal(entries, title, plot_max, output_file):
    fig, ax = plt.subplots(figsize=(9, 2.4))
    ax.set_title(title)

    ordered = entries
    xpos = np.arange(len(ordered))
    values = [throughput(result) for _, result, _ in ordered]
    rects = ax.bar(
        xpos,
        values,
        .8,
        tick_label=[name for i, (name, _, _) in enumerate(ordered)],
    )

    for rect, (_, result, status), value in zip(rects, ordered, values):
        x = rect.get_x() + rect.get_width() / 2
        if result:
            ax.text(x, value + plot_max * 0.01, f"{value:.2f} MB/s", va="bottom", ha="center")
        else:
            color = "red" if status == "failed" else "dimgray"
            ax.text(x, plot_max * 0.02, status, va="bottom", ha="center", color=color)

    ax.set_ylabel('Throughput in MB/s')
    ax.set_xlim(-0.5, len(ordered) - 0.5)
    ax.set_ylim(0, plot_max)

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close(fig)

def plot(scenario, blocking, non_blocking):
    max_b = max([throughput(result) for _, result, _ in blocking] or [0])
    max_nb = max([throughput(result) for _, result, _ in non_blocking] or [0])
    max_all = max((max_b, max_nb))

    plot_one_horizontal(
        non_blocking,
        f"Scenario {scenario.name!r} (non-blocking)",
        (max_nb or 1.0) * 1.2,
        f"plots/{scenario.name}-non-blocking.svg",
    )
    plot_one_horizontal(
        blocking,
        f"Scenario {scenario.name!r} (blocking)",
        (max_b or 1.0) * 1.2,
        f"plots/{scenario.name}-blocking.svg",
    )

if __name__ == "__main__":
    for scenario in SCENARIOS:
        print(scenario.name)

        set1 = []
        set2 = []

        for name, (blocking, non_blocking) in parser_table.items():
            result, status = parser_status(scenario, blocking)
            set1.append((name, result, status))

            result, status = parser_status(scenario, non_blocking)
            set2.append((name, result, status))
        
        plot(scenario, set1, set2)
