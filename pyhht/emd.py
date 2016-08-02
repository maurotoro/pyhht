#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2015 jaidev <jaidev@newton>
#
# Distributed under terms of the MIT license.

"""Empirical Mode Decomposition."""

import numpy as np
from numpy import pi
import warnings
from scipy.interpolate import splrep, splev
from pyhht.utils import extr, boundary_conditions


class EmpiricalModeDecomposition(object):
    """Empirical mode decomposition implemented as a class.

    Parameters
    ----------
        x : array-like
            A vector on which to perform empirical mode decomposition.
    
        t : array-like
            Sampling time instants.
        
        threshold_1 : float
            Threshold for the stopping criterion, corresponding to
            :math:`\theta_{1}` in [1] (Default: 0.05)
        
        threshold_2 : float
            Threshold for the stopping criterion, corresponding to
            :math:`\theta_{2}` in [1] (Default: 0.5)
        
        alpha : float
            Tolerance for the stopping criterion, corresponding to
            :math:`\alpha` in [1] (Default: 0.05)
        
        is_mode_complex : bool
            Whether the input signal is complex.

        ndirs : int
            Number of directions in which envelopes are computed.
            (Default: 4)
        
        fixe : int
            Number of sifting iterations to perform for each mode. The
            default value is ``None``, in which case the default stopping criterion
            is used. If not ``None``, each mode will be a result of exactly
            ``fixe`` sifting iterations.
        
        maxiter : int
            Number of maximum sifting iterations for the
            computation of each mode. (Default: 2000)
        
        fixe_h : int

        n_imfs : int
            Number if IMFs to extract.
        
        nbsym : int
            Number of points to mirror when calculating envelopes.
        
    Returns 
    -------
        EMD : numpy.ndarray
            Array of shape [n_imfs + 1, length(x)]

    Example:
    -------
        >>> from pyhht.visualization import plot_imfs
        >>> t = linspace(0, 1, 1000)
        >>> modes = sin(2 * pi * 5 * t) + sin(2 * pi * 10 * t)
        >>> x = modes + t
        >>> decomposer = EMD(x)
        >>> imfs = decomposer.decompose()
        >>> plot_imfs(x, t, imfs)

        .. plot:: ../../docs/examples/simple_emd.py
        """


    def __init__(self, x, t=None, threshold_1=0.05, threshold_2=0.5, alpha=0.05,
                 is_mode_complex=None, ndirs=4, fixe=0, maxiter=2000,
                 fixe_h=0, n_imfs=0, nbsym=2):
        """ Empirical Mode Decomposition Class instantiation"""
        self.threshold_1 = threshold_1
        self.threshold_2 = threshold_2
        self.alpha = alpha
        self.maxiter = maxiter
        self.fixe_h = fixe_h
        self.ndirs = ndirs
        self.complex_version = 2
        self.nbit = 0
        self.Nbit = 0
        self.n_imfs = n_imfs
        self.k = 1
        # self.mask = mask
        self.nbsym = nbsym
        self.nbit = 0
        self.NbIt = 0

        if x.ndim > 1:
            if 1 not in x.shape:
                raise ValueError("x must have only one row or one column.")
        if x.shape[0] > 1:
            x = x.ravel()
        if not np.all(np.isfinite(x)):
            raise ValueError("All elements of x must be finite.")
        self.x = x
        self.ner = self.nzr = len(self.x)
        self.residue = self.x.copy()

        if t is None:
            self.t = np.arange(np.max(x.shape))
        else:
            if t.shape != self.x.shape:
                raise ValueError("t must have the same dimensions as x.")
            if t.ndim > 1:
                if 1 not in t.shape:
                    raise ValueError("t must have only one column or one row.")
            if not np.all(np.isreal(t)):
                raise TypeError("t must be a real vector.")
            if t.shape[0] > 1:
                t = t.ravel()
            self.t = t

        self.sdt = self.threshold_1 * np.ones((len(self.x),))
        self.sd2t = self.threshold_2 * np.ones((len(self.x),))

        if fixe:
            self.maxiter = fixe
            if self.fixe_h:
                raise TypeError("Cannot use both fixe and fixe_h modes")
        self.fixe = fixe

        # FIXME: `is_mode_complex` should be a boolean and self.complex_version
        # should be a string for better readability. Also, the boolean should
        # be redundant in the signature of __init__
        if is_mode_complex is None:
            is_mode_complex = not(np.all(np.isreal(self.x) * self.complex_version))
        self.is_mode_complex = is_mode_complex

        self.imf = []
        self.nbits = []

        # FIXME: Masking disabled because it seems to be recursive.
#        if np.any(mask):
#            if mask.shape != x.shape:
#                raise TypeError("Masking signal must have the same dimensions" +
#                                "as the input signal x.")
#            if mask.shape[0]>1:
#                mask = mask.ravel()
#            imf1 = emd(x+mask, opts)

    def io(self):
        """Compute the index of orthoginality, as defined by:

            .. math:: \sum_{i, j=1, i\neq j}^{N} \frac{\|C_{i}\overline{C_{j}}\|}{\|x\|^2}

        Where :math:`C_{i}` is the :math:`i` th IMF.

        returns : float
            Index of orthogonality.
        
        Example:
        -------
        >>> t = linspace(0, 1, 1000)
        >>> modes = sin(2 * pi * 5 * t) + sin(2 * pi * 10 * t)
        >>> x = modes + t
        >>> decomposer = EMD(x)
        >>> decomposer.decompose()
        >>> print(decomposer.io())
        0.0516420404972
        """

        n = len(self.imf)
        s = 0
        for i in range(n):
            for j in range(n):
                if i != j:
                    s += np.abs(np.sum(self.imf[i] * np.conj(self.imf[j])) / np.sum(self.x**2))
        return 0.5 * s

    def stop_EMD(self):
        """Check if there are enough extrema (3) to continue sifting."""
        if self.is_mode_complex:
            ner = []
            for k in range(self.ndirs):
                phi = k * pi / self.ndirs
                indmin, indmax, _ = extr(np.real(np.exp(1j * phi) * self.residue))
                ner.append(len(indmin) + len(indmax))
            stop = np.any(ner < 3)
        else:
            indmin, indmax, _ = extr(self.residue)
            ner = len(indmin) + len(indmax)
            stop = ner < 3
        return stop

    def mean_and_amplitude(self, m):
        """ Computes the mean of the envelopes and the mode amplitudes."""
        # FIXME: The spline interpolation may not be identical with the MATLAB
        # implementation. Needs further investigation.
        if self.is_mode_complex:
            if self.is_mode_complex == 1:
                nem = []
                nzm = []
                envmin = np.zeros((self.ndirs, len(self.t)))
                envmax = np.zeros((self.ndirs, len(self.t)))
                for k in range(self.ndirs):
                    phi = k * pi / self.ndirs
                    y = np.real(np.exp(-1j * phi) * m)
                    indmin, indmax, indzer = extr(y)
                    nem.append(len(indmin) + len(indmax))
                    nzm.append(len(indzer))
                    tmin, tmax, zmin, zmax = boundary_conditions(y, self.t, m,
                                                                 self.nbsym)

                    f = splrep(tmin, zmin)
                    spl = splev(self.t, f)
                    envmin[k, :] = spl

                    f = splrep(tmax, zmax)
                    spl = splev(self.t, f)
                    envmax[k, :] = spl

                envmoy = np.mean((envmin + envmax) / 2, axis=0)
                amp = np.mean(abs(envmax - envmin), axis=0) / 2

            elif self.is_mode_complex == 2:
                nem = []
                nzm = []
                envmin = np.zeros((self.ndirs, len(self.t)))
                envmax = np.zeros((self.ndirs, len(self.t)))
                for k in range(self.ndirs):
                    phi = k * pi / self.ndirs
                    y = np.real(np.exp(-1j * phi) * m)
                    indmin, indmax, indzer = extr(y)
                    nem.append(len(indmin) + len(indmax))
                    nzm.append(len(indzer))
                    tmin, tmax, zmin, zmax = boundary_conditions(y, self.t, m,
                                                                 self.nbsym)
                    f = splrep(tmin, zmin)
                    spl = splev(self.t, f)
                    envmin[k, ] = np.exp(1j * phi) * spl

                    f = splrep(tmax, zmax)
                    spl = splev(self.t, f)
                    envmax[k, ] = np.exp(1j * phi) * spl

                envmoy = np.mean((envmin + envmax), axis=0)
                amp = np.mean(abs(envmax - envmin), axis=0) / 2

        else:
            indmin, indmax, indzer = extr(m)
            nem = len(indmin) + len(indmax)
            nzm = len(indzer)
            tmin, tmax, mmin, mmax = boundary_conditions(m, self.t, m, self.nbsym)

            f = splrep(tmin, mmin)
            envmin = splev(self.t, f)

            f = splrep(tmax, mmax)
            envmax = splev(self.t, f)

            envmoy = (envmin + envmax) / 2
            amp = np.abs(envmax - envmin) / 2.0

        return envmoy, nem, nzm, amp

    def stop_sifting(self, m):
        """Evaluate the stopping criteria for the current mode.
        
        Parameters
        ----------
        m : array-like
            The current mode
        """
        # FIXME: This method needs a better name.
        if self.fixe:
            stop_sift, moyenne = self.mean_and_amplitude(), 0
        elif self.fixe_h:
            stop_count = 0
            try:
                moyenne, nem, nzm = self.mean_and_amplitude(m)[:3]

                if np.all(abs(nzm - nem) > 1):
                    stop = 0
                    stop_count = 0
                else:
                    stop_count += 1
                    stop = (stop_count == self.fixe_h)
            except:
                moyenne = np.zeros((len(m)))
                stop = 1
            stop_sift = stop
        else:
            try:
                envmoy, nem, nzm, amp = self.mean_and_amplitude(m)
            except TypeError as err:
                if err.args[0] == "m > k must hold":
                    return 1, np.zeros((len(m)))
            except ValueError as err:
                if err.args[0] == "Not enough extrema.":
                    return 1, np.zeros((len(m)))
            sx = np.abs(envmoy) / amp
            stop = not(((np.mean(sx > self.threshold_1) > self.alpha) or
                        np.any(sx > self.threshold_2)) and np.all(nem > 2))
            if not self.is_mode_complex:
                stop = stop and not(np.abs(nzm - nem) > 1)
            stop_sift = stop
            moyenne = envmoy
        return stop_sift, moyenne

    def keep_decomposing(self):
        """Check whether to continue the sifting operation."""
        return not(self.stop_EMD()) and \
            (self.k < self.n_imfs + 1 or self.n_imfs == 0)  # and \
# not(np.any(self.mask))

    def decompose(self):
        """Decompose the input signal into IMFs.

        This function does all the heavy lifting required for sifting, and
        should ideally be the only public method of this class."""
        while self.keep_decomposing():

            # current mode
            m = self.residue

            # computing mean and stopping criterion
            stop_sift, moyenne = self.stop_sifting(m)

            # in case current mode is small enough to cause spurious extrema
            if np.max(np.abs(m)) < (1e-10) * np.max(np.abs(self.x)):
                if not stop_sift:
                    warnings.warn("EMD Warning: Amplitude too small, stopping.")
                else:
                    print("Force stopping EMD: amplitude too small.")
                return

            # SIFTING LOOP:
            while not(stop_sift) and (self.nbit < self.maxiter):

                if (not(self.is_mode_complex) and (self.nbit > self.maxiter / 5) and
                        self.nbit % np.floor(self.maxiter / 10) == 0 and
                        not(self.fixe) and self.nbit > 100):
                    print("Mode " + str(self.k) + ", Iteration " + str(self.nbit))
                    im, iM, _ = extr(m)
                    print(str(np.sum(m[im] > 0)) + " minima > 0; " + str(np.sum(m[im] < 0)) + " maxima < 0.")

                # Sifting
                m = m - moyenne

                # Computing mean and stopping criterion
                if self.fixe:
                    stop_sift, moyenne = self.stop_sifting_fixe()
                elif self.fixe_h:
                    stop_sift, moyenne, stop_count = self.stop_sifting_fixe_h()
                else:
                    stop_sift, moyenne = self.stop_sifting(m)

                self.nbit += 1
                self.NbIt += 1

                if (self.nbit == (self.maxiter - 1)) and not(self.fixe) and (self.nbit > 100):
                    warnings.warn("Emd:warning, Forced stop of sifting - " +
                                  "Maximum iteration limit reached.")

            self.imf.append(m)

            self.nbits.append(self.nbit)
            self.k += 1

            self.residue = self.residue - m
            self.ort = self.io()

        if np.any(self.residue):
            self.imf.append(self.residue)
        return np.array(self.imf)

EMD = EmpiricalModeDecomposition
