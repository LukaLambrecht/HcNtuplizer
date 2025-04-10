import os
import sys
import json
import argparse
import numpy as np
import awkward as ak
import matplotlib.pyplot as plt

thisdir = os.path.abspath(os.path.dirname(__file__))
topdir = os.path.abspath(os.path.join(thisdir, '../'))
sys.path.append(topdir)

from plotting.plot import plot
from tools.plottools import make_hist
from tools.variabletools import read_variables
from tools.samplelisttools import read_samplelist


if __name__=='__main__':

    # read command line args
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--sim', required=True)
    parser.add_argument('-d', '--data', default=None)
    parser.add_argument('-v', '--variables', required=True)
    parser.add_argument('-o', '--outputdir', required=True)
    parser.add_argument('--dolog', default=False, action='store_true')
    parser.add_argument('--extracmstext', default=None)
    parser.add_argument('--lumiheader', default=None)
    parser.add_argument('--extrainfo', default=None)
    parser.add_argument('--entry_start', default=None)
    parser.add_argument('--entry_stop', default=None)
    args = parser.parse_args()

    # read variables
    variables = read_variables(args.variables)
    variablelist = [v.variable for v in variables]

    # set branches to read
    branches_to_read = variablelist
    branches_to_read.append('nH')
    branches_to_read_sim = branches_to_read[:]
    branches_to_read_sim.append('genWeight')
    branches_to_read_sim.append('lumiwgt')
    branches_to_read_sim.append('xsecWeight')

    # read the input files
    treename = 'Events'
    print('Reading ntuples...')
    events = read_samplelist(args.sim,
                          mode='uproot',
                          treename=treename,
                          branches=branches_to_read_sim,
                          entry_start=args.entry_start,
                          entry_stop=args.entry_stop)
    sim_keys = list(events.keys())
    data_keys = []
    if args.data is not None:
        events_data = read_samplelist(args.data,
                          mode='uproot',
                          treename=treename,
                          branches=branches_to_read,
                          entry_start=args.entry_start,
                          entry_stop=args.entry_stop)
        data_keys = list(events_data.keys())
        events = {**events, **events_data}

    # filter events with one H candidate
    print('Filter on exactly 1 H candidate:')
    for key, sample in events.items():
        nH = sample['nH'].to_numpy()
        mask = (nH==1).astype(bool)
        events[key] = sample[mask]
        print(f'  - sample {key}: {np.sum(mask)} / {len(mask)} entries')

    # flatten all variables
    new_events = {}
    for key, sample in events.items():
        new_sample = {}
        for variable in sample.fields:
            new_sample[variable] = ak.flatten(sample[variable], axis=None)
        new_sample = ak.Array(new_sample)
        new_events[key] = new_sample
    events = new_events

    # set colors
    colordict = {
        'Hc': 'red',
        'Hb': 'darkorchid',
        'ggH': 'orchid',
        'VBF': 'plum',
        'qqZZ': 'dodgerblue',
        'ggZZ': 'mediumslateblue'
    }

    # set labels
    labeldict = {
        'Hc': 'H+c',
        'Hb': 'H+b',
        'ggH': 'H (ggH)',
        'VBF': 'H (VBF)',
        'ggZZ': 'ZZ (ggZZ)',
        'qqZZ': 'ZZ (qqZZ)'
    }

    # set styles
    styledict = {
        'Hc': 'fill',
        'Hb': 'fill',
        'ggH': 'fill',
        'VBF': 'fill',
        'ggZZ': 'fill',
        'qqZZ': 'fill'
    }

    # make output directory
    if not os.path.exists(args.outputdir):
        os.makedirs(args.outputdir)

    # loop over variables
    for varidx, variable in enumerate(variables):
        print(f'Plotting variable {variable.name}')
        
        # make histograms
        hists = {}
        for key, sample in events.items():
            values = sample[variable.variable].to_numpy().astype(float)
            weights = None
            if key in sim_keys:
                genweight = sample['genWeight'].to_numpy().astype(float)
                lumiweight = sample['lumiwgt'].to_numpy().astype(float)
                xsecweight = sample['xsecWeight'].to_numpy().astype(float)
                weights = np.multiply(np.multiply(lumiweight, xsecweight), genweight)
            hists[key] = make_hist(values, variable, weights=weights)

        # split in sim and data
        hists_sim = {key: val for key, val in hists.items() if key in sim_keys}
        hists_data = {key: val for key, val in hists.items() if key in data_keys}
        if len(hists_data)==0: hist_data = None
        elif len(hists_data)==1: hist_data = hists_data
        else: raise Exception('Unexptected number of data processes.')

        # loop over plot options
        stacklist = sim_keys[:]
        #stacklist = None
        log = [False]
        if args.dolog: log.append(True)
        for logscale in log:

            # make plot
            yaxtitle = 'Events'
            fig, ax = plot(bkg=hists_sim, data=hist_data,
                       stacklist=stacklist,
                       variable=variable,
                       colordict=colordict,
                       labeldict=labeldict,
                       styledict=styledict,
                       normalize=False,
                       logscale=logscale,
                       extracmstext=args.extracmstext,
                       lumiheader=args.lumiheader,
                       yaxtitle=yaxtitle,
                       dolegend=True)

            # add some extra info
            if args.extrainfo is not None:
                ax.text(0.02, 0.9, args.extrainfo, ha='left', va='top',
                        transform=ax.transAxes, fontsize=12)

            # save the figure
            fig.tight_layout()
            figname = variable.name
            if logscale: figname += '_log'
            figname += '.png'
            figname = os.path.join(args.outputdir, figname)
            fig.savefig(figname)
            plt.close(fig)
