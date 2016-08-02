#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2015 jaidev <jaidev@newton>
#
# Distributed under terms of the MIT license.

"""Visualization functions for PyHHT."""


import matplotlib.pyplot as plt
import numpy as np


def plot_imfs(signal, imfs, time_samples=None, fignum=None):
    """Visualize decomposed signals.

    Parameters
    ----------
    signal : array-like
        Analyzed signal

    time_samples : array-like
        time instants

    imfs : array-like, shape (n_imfs, lenght_of_signal)
        intrinsic mode functions of the signal

    fignum : int
        (optional) number of the figure to display

    Returns
    -------
    None

    Example:
    -------

    >>> plot_imfs(signal)

    .. plot:: ../../docs/examples/emd_fmsin.py
    """
    if time_samples is None:
        time_samples = np.arange(signal.shape[0])

    n_imfs = imfs.shape[0]

    plt.figure(num=fignum)
    axis_extent = max(np.max(np.abs(imfs[:-1, :]), axis=0))

    # Plot original signal
    ax = plt.subplot(n_imfs, 1, 1)
    ax.plot(time_samples, signal)
    ax.axis([time_samples[0], time_samples[-1], signal.min(), signal.max()])
    ax.tick_params(which='both', left=False, bottom=False, labelleft=False,
            labelbottom=False)
    ax.grid(False)
    ax.set_ylabel('Signal')
    ax.set_title('Empirical Mode Decomposition')

    # Plot the IMFs
    for i in range(n_imfs - 1):
        ax = plt.subplot(n_imfs, 1, i + 2)
        ax.plot(time_samples, imfs[i, :])
        ax.axis([time_samples[0], time_samples[-1], -axis_extent, axis_extent])
        ax.tick_params(which='both', left=False, bottom=False, labelleft=False,
                labelbottom=False)
        ax.grid(False)
        ax.set_ylabel('imf' + str(i + 1))

    # Plot the residue
    ax = plt.subplot(n_imfs + 1, 1, n_imfs + 1)
    ax.plot(time_samples, imfs[-1, :], 'r')
    ax.axis('tight')
    ax.tick_params(which='both', left=False, bottom=False, labelleft=False,
            labelbottom=False)
    ax.grid(False)
    ax.set_ylabel('res.')

    plt.show()
