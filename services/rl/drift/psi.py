#!/usr/bin/env python3
import math


def psi(expected_bins, actual_bins, eps=1e-12):
    # expected_bins/actual_bins: list of bin counts (same length)
    e_sum = sum(expected_bins) or 1.0
    a_sum = sum(actual_bins) or 1.0
    s = 0.0
    for e, a in zip(expected_bins, actual_bins):
        p = max(e / e_sum, eps)
        q = max(a / a_sum, eps)
        s += (q - p) * math.log(q / p)
    return s


def bucket(values, edges):
    # returns list counts per bin
    bins = [0] * (len(edges) - 1)
    for v in values:
        for i in range(len(edges) - 1):
            if edges[i] <= v < edges[i + 1]:
                bins[i] += 1
                break
    return bins
