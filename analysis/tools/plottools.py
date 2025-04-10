import os
import sys
import json
import numpy as np
import awkward as ak
from fnmatch import fnmatch

thisdir = os.path.abspath(os.path.dirname(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../'))
sys.path.append(topdir)


def make_hist(values, variable, weights=None, clipmin=None):
    if weights is None: weights = np.ones(len(values)).astype(float)
    hist = np.histogram(values, bins=variable.bins, weights=weights)[0]
    staterrors = np.sqrt(np.histogram(values, bins=variable.bins,
                   weights=np.square(weights))[0])
    if clipmin is not None: hist = np.clip(hist, a_min=clipmin, a_max=None)
    return (hist, staterrors)

def make_hist_from_events(events, variable, weightkey=None, **kwargs):
    values = events[variable.variable].to_numpy().astype(float)
    weights = None
    if weightkey is not None: weights = events[weightkey].to_numpy().astype(float)
    return make_hist(values, variable, weights=weights, **kwargs)

def merge_events(events, mergedict, verbose=False):
    merged_events = {}
    all_mkeys = []
    for key, val in mergedict.items():
        mkeys = []
        for pattern in val: mkeys += [k for k in events.keys() if fnmatch(k, pattern)]
        mkeys = list(set(mkeys))
        if len(mkeys)==0: continue
        all_mkeys += mkeys
        if verbose: print(f'  - Creating merged sample {key} from original samples {mkeys}')
        merged_events[key] = ak.concatenate([events[k] for k in mkeys])
    for key in events.keys():
        if key not in all_mkeys:
            if verbose: print(f'  - Keeping sample {key} without merging')
            merged_events[key] = events[key]
    return merged_events
