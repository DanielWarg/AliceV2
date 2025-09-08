#!/usr/bin/env python3
def ks_stat(sample_a, sample_b):
    a = sorted(sample_a)
    b = sorted(sample_b)
    ia = ib = 0
    na = len(a)
    nb = len(b)
    d = 0.0
    while ia < na and ib < nb:
        if a[ia] <= b[ib]:
            ia += 1
        else:
            ib += 1
        d = max(d, abs(ia / na - ib / nb))
    return d
