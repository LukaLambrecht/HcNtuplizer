import os
import sys
import json
import mplhep
import argparse
import numpy as np
import matplotlib.pyplot as plt


def plot(sig=None, bkg=None, data=None,
         variable=None,
         fig=None, ax=None,
         stacklist=None,
         colordict=None, labeldict=None, styledict=None,
         normalize=False, logscale=False,
         docms=True, extracmstext=None, lumiheader=None,
         yaxtitle=None, dolegend=False):
    # Input arguments:
    # - sig and bkg: dicts of the form {<label>: (np array, np array), ...},
    #   where the first array in the tuple represents the bin contents,
    #   and the second one the (statistical) uncertainties.
    # - data: dict of the same form as sig and bkg, but with only one item.

    # concatenate dicts of sig and bkg histograms
    # (distinction between sig and bkg is not used in this function for now)
    all_hists = {}
    if bkg is not None:
        for key, val in bkg.items(): all_hists[key] = val
    if sig is not None:
        for key, val in sig.items(): all_hists[key] = val

    # split data tuple in actual histogram and uncertainties,
    # and some other data properties
    if data is not None:
        if len(data)!=1:
            msg = f'Unexptected number of items in data dict: {data}'
            raise Exception(msg)
        data_key = list(data.keys())[0]
        data_hist = data[data_key][0]
        data_staterrors = data[data_key][1]
        data_label = labeldict.get(data_key, 'Data')
        data_markersize = 2

    # make lists for sig and bkg histograms
    # and corresponding settings
    hists = [all_hists[key][0] for key in all_hists.keys()]
    staterrors = [all_hists[key][1] for key in all_hists.keys()]
    stack_ids = []
    nostack_ids = list(range(len(hists)))
    if stacklist is not None:
        stack_ids = [idx for idx, key in enumerate(all_hists.keys()) if key in stacklist]
        nostack_ids = [idx for idx, key in enumerate(all_hists.keys()) if key not in stacklist]
    colors = None
    if colordict is not None:
        colors = [colordict.get(key, 'grey') for key in all_hists.keys()]
    labels = None
    if labeldict is not None:
        labels = [labeldict.get(key, '') for key in all_hists.keys()]
    styles = ['step']*len(hists)
    if styledict is not None:
        styles = [styledict.get(key, 'step') for key in all_hists.keys()]

    # normalize to unit surface area if requested
    if normalize:
        if data is not None:
            integral = np.sum(data_hist)
            if variable is not None:
                integral = np.sum( np.multiply(data_hist, variable.bins[1:]-variable.bins[:-1]) )
            if integral > 0:
                data_hist /= integral
                data_staterrors /= integral
        for idx, (hist, staterror) in enumerate(zip(hists, staterrors)):
            integral = np.sum(hist)
            if variable is not None:
                integral = np.sum( np.multiply(hist, variable.bins[1:]-variable.bins[:-1]) )
            if integral > 0:
                hists[idx] /= integral
                staterrors[idx] /= integral

    # for stacked histograms, calculate nominal sum and total error
    histsum = np.zeros(hists[0].shape)
    staterrorsum = np.zeros(hists[0].shape)
    for idx in stack_ids:
        histsum += hists[idx]
        staterrorsum += np.square(staterrors[idx])
    staterrorsum = np.sqrt(staterrorsum)
    if normalize:
        integral = np.sum(histsum)
        if variable is not None:
            integral = np.sum( np.multiply(histsum, variable.bins[1:]-variable.bins[:-1]) )
        if integral > 0:
            histsum /= integral
            staterrorsum /= integral
            for idx in stack_ids:
                hists[idx] /= integral
                staterrors[idx] /= integral

    # make the base figure
    if fig is None or ax is None: fig, ax = plt.subplots(figsize=(8,6))

    # plot stacked histograms
    if len(stack_ids)>0:

        # nominal
        mplhep.histplot(
          [hists[idx] for idx in stack_ids],
          stack = True,
          bins = variable.bins if variable is not None else None,
          #histtype = [styles[idx] for idx in stack_ids], # a list does not work here...
          histtype = styles[stack_ids[0]],
          color = [colors[idx] for idx in stack_ids],
          edgecolor = [colors[idx] for idx in stack_ids],
          label = [labels[idx] for idx in stack_ids],
          ax=ax)

        # statistical error
        ax.stairs(histsum+staterrorsum, baseline=histsum-staterrorsum,
                  edges=variable.bins if variable is not None else None,
                  fill=True, color='grey', alpha=0.3)

    # plot non-stacked histograms
    for idx in nostack_ids:

        # set transparency
        alpha = 1
        if styles[idx]=='fill': alpha = 0.7

        # nominal
        mplhep.histplot(
          hists[idx],
          stack = False,
          bins = variable.bins if variable is not None else None,
          histtype = styles[idx],
          color = colors[idx],
          alpha = alpha,
          edgecolor = colors[idx],
          label = labels[idx],
          ax=ax
        )

        # statistical error
        ax.stairs(hists[idx]+staterrors[idx], baseline=hists[idx]-staterrors[idx],
                  edges=variable.bins if variable is not None else None,
                  fill=True, color=colors[idx], alpha=0.3)

    # plot data
    if data is not None:
        bincenters = None
        # todo: the plot will crash if bincenters is not set,
        #       i.e. if no variable is provided; find good default setting.
        if variable is not None:
            bincenters = (variable.bins[:-1] + variable.bins[1:]) / 2.
        ax.errorbar(bincenters, data_hist,
            xerr=None, yerr=data_staterrors,
            linestyle="None", color="black",
            marker="o", markersize=data_markersize, label=data_label)

    # some plot aesthetics
    ax.minorticks_on()
    if logscale: ax.set_yscale('log')
    if docms:
        cmstext = r'$\bf{CMS}$'
        if extracmstext is not None: cmstext += r' $\it{' + f' {extracmstext}' + r'}$'
        ax.text(0.02, 0.98, cmstext,
                ha='left', va='top', fontsize=15, transform=ax.transAxes)
        # modify the axis range to accommodate the CMS text
        if logscale:
            yscale = ax.get_ylim()[1]/ax.get_ylim()[0]
            ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1]*yscale**(0.2))
        else:
            yscale = ax.get_ylim()[1] - ax.get_ylim()[0]
            ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1] + yscale*0.2)
    if lumiheader is not None:
        ax.text(1., 1., lumiheader,
                ha='right', va='bottom', fontsize=15, transform=ax.transAxes)
    if variable is not None and variable.axtitle is not None:
        xaxtitle = variable.axtitle
        if variable.unit is not None and len(variable.unit)>0:
            xaxtitle += f' [{variable.unit}]'
        ax.set_xlabel(xaxtitle, fontsize=15)
    if yaxtitle is not None: ax.set_ylabel(yaxtitle, fontsize=15)
    if dolegend:
        # if number of labels is large, put legend outside the axes
        bbox_to_anchor = None
        loc = None
        if len(hists) > 5:
            loc = 'upper left'
            bbox_to_anchor = (1., 1.)
        ax.legend(loc=loc, bbox_to_anchor=bbox_to_anchor, fontsize=10)

    return fig, ax
