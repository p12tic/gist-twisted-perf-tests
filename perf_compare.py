#!/usr/bin/env python3

import argparse
import json

import perf_utils

def read_results_from_file(path):
    with open(path) as in_f:
        return perf_utils.PerfResults.from_json(json.load(in_f))


def get_diff(a, b):
    times_diff = (b - a) / min(b, a)
    sign = '-' if times_diff < 0 else '+'

    # 1.00x diff is zero, 2.00x diff is two times faster or slower
    times_diff = abs(times_diff) + 1
    return sign, times_diff


def main():
    parser = argparse.ArgumentParser(prog='perf_compare')
    parser.add_argument('path_a', type=str)
    parser.add_argument('path_b', type=str)
    args = parser.parse_args()

    results_a = read_results_from_file(args.path_a)
    results_b = read_results_from_file(args.path_b)

    max_name_len = max(len(name) for name in results_a.names)

    lines = []

    for name in results_a.names:
        r_a = results_a.results[name]
        r_b = results_b.results[name]

        sign, times_diff = get_diff(r_a.value, r_b.value)

        line = '{0}: {1:.2f}us vs {2:.2f}us ({3}{4:.3f}x diff)'.format(
            name.ljust(max_name_len), r_a.value, r_b.value, sign,
            times_diff)
        lines.append(line)

        if r_a.base_name is not None:
            assert r_a.base_name == r_b.base_name
            br_a = results_a.results[r_a.base_name]
            br_b = results_b.results[r_b.base_name]

            a_value = r_a.value - br_a.value
            b_value = r_b.value - br_b.value

            sign, times_diff = get_diff(a_value, b_value)

            lines.append('{0}: without overhead evaluated in {1}:'.format(
                ''.ljust(max_name_len), r_a.base_name))
            line = '{0}: {1:.2f}us vs {2:.2f}us ({3}{4:.3f}x diff)'.format(
                ''.ljust(max_name_len), a_value, b_value, sign, times_diff)

            lines.append(line)
            lines.append('')

    print('\n'.join(lines))

if __name__ == '__main__':
    main()
