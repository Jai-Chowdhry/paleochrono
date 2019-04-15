#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  7 16:55:54 2019
Module for the SitePair class.
@author: parrenif
"""

import os
import numpy as np
import matplotlib.pyplot as mpl
from matplotlib.backends.backend_pdf import PdfPages
from scipy.linalg import lu_factor, lu_solve
from scipy.linalg import cholesky
import pccfg

class SitePair(object):
    """Class for a pair of sites."""

    def __init__(self, site1, site2):
        self.site1 = site1
        self.site2 = site2
        self.label = self.site1.label+'-'+self.site2.label


#TODO: allow to have either dlabel1+'-'dlabel2 or dlbel2+'-'dlabel1 as directory
        if self.site1.archive == 'icecore' and self.site2.archive == 'icecore':
            filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+\
                       '/iceice_synchro_horizons.txt'
            if not os.path.isfile(filename):
                filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+'/ice_depth.txt'
        elif self.site1.archive == 'icecore' or self.site2.archive == 'icecore':
            filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+\
                       '/ice_synchro_horizons.txt'
        else:
            filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+'/synchro_horizons.txt'
        if os.path.isfile(filename) and open(filename).read():
            readarray = np.loadtxt(filename)
            self.iceicehorizons_depth1 = readarray[:, 0]
            self.iceicehorizons_depth2 = readarray[:, 1]
            self.iceicehorizons_sigma = readarray[:, 2]
        else:
            self.iceicehorizons_depth1 = np.array([])
            self.iceicehorizons_depth2 = np.array([])
            self.iceicehorizons_sigma = np.array([])
        self.iceicehorizons_correlation = np.diag(np.ones(np.size(self.iceicehorizons_depth1)))

        if self.site1.archive == 'icecore' and self.site2.archive == 'icecore':
            filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+\
                       '/airair_synchro_horizons.txt'
            if not os.path.isfile(filename):
                filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+'/air_depth.txt'
            if os.path.isfile(filename) and open(filename).read():
                readarray = np.loadtxt(filename)
                self.airairhorizons_depth1 = readarray[:, 0]
                self.airairhorizons_depth2 = readarray[:, 1]
                self.airairhorizons_sigma = readarray[:, 2]
            else:
                self.airairhorizons_depth1 = np.array([])
                self.airairhorizons_depth2 = np.array([])
                self.airairhorizons_sigma = np.array([])
            self.airairhorizons_correlation = np.diag(np.ones(np.size(self.airairhorizons_depth1)))

        if self.site2.archive == 'icecore':
            if self.site1.archive == 'icecore':
                filename = pccfg.DATADIR+self.site1.label+'-'+\
                            self.site2.label+'/iceair_synchro_horizons.txt'
                if not os.path.isfile(filename):
                    filename = pccfg.DATADIR+self.site1.label+'-'+\
                                self.site2.label+'/iceair_depth.txt'
            else:
                filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+\
                           '/air_synchro_horizons.txt'
            if os.path.isfile(filename) and open(filename).read():
                readarray = np.loadtxt(filename)
                self.iceairhorizons_depth1 = readarray[:, 0]
                self.iceairhorizons_depth2 = readarray[:, 1]
                self.iceairhorizons_sigma = readarray[:, 2]
            else:
                self.iceairhorizons_depth1 = np.array([])
                self.iceairhorizons_depth2 = np.array([])
                self.iceairhorizons_sigma = np.array([])
            self.iceairhorizons_correlation = np.diag(np.ones(np.size(self.iceairhorizons_depth1)))

        if self.site1.archive == 'icecore':
            if self.site2.archive == 'icecore':
                filename = pccfg.DATADIR+self.site1.label+'-'+\
                            self.site2.label+'/airice_synchro_horizons.txt'
                if not os.path.isfile(filename):
                    filename = pccfg.DATADIR+self.site1.label+'-'+\
                                self.site2.label+'/airice_depth.txt'
            else:
                filename = pccfg.DATADIR+self.site1.label+'-'+self.site2.label+\
                           '/air_synchro_horizons.txt'
            if os.path.isfile(filename) and open(filename).read():
                readarray = np.loadtxt(filename)
                self.airicehorizons_depth1 = readarray[:, 0]
                self.airicehorizons_depth2 = readarray[:, 1]
                self.airicehorizons_sigma = readarray[:, 2]
            else:
                self.airicehorizons_depth1 = np.array([])
                self.airicehorizons_depth2 = np.array([])
                self.airicehorizons_sigma = np.array([])
            self.airicehorizons_correlation = np.diag(np.ones(np.size(self.airicehorizons_depth1)))


        filename = pccfg.DATADIR+'/parameters_covariance_observations_all_site_pairs.py'
        filename2 = pccfg.DATADIR+'/parameters-CovarianceObservations-AllDrillings.py'
        if os.path.isfile(filename):
            exec(open(filename).read())
        elif os.path.isfile(filename2):
            exec(open(filename2).read())
        filename = pccfg.DATADIR+self.label+'/parameters_covariance_observations.py'
        filename2 = pccfg.DATADIR+self.label+'/parameters-CovarianceObservations.py'
        if os.path.isfile(filename):
            exec(open(filename).read())
        elif os.path.isfile(filename2):
            exec(open(filename2).read())
        if np.size(self.iceicehorizons_depth1) > 0:
            self.iceicehorizons_chol = cholesky(self.iceicehorizons_correlation)
            self.iceicehorizons_lu_piv = lu_factor(self.iceicehorizons_chol)
        if self.site1.archive == 'icecore' and self.site2.archive == 'icecore':
            if np.size(self.airairhorizons_depth1) > 0:
                self.airairhorizons_chol = cholesky(self.airairhorizons_correlation)
                self.airairhorizons_lu_piv = lu_factor(self.airairhorizons_chol)
        if self.site2.archive == 'icecore':
            if np.size(self.iceairhorizons_depth1) > 0:
                self.iceairhorizons_chol = cholesky(self.iceairhorizons_correlation)
                self.iceairhorizons_lu_piv = lu_factor(self.iceairhorizons_chol)
        if self.site1.archive == 'icecore':
            if np.size(self.airicehorizons_depth1) > 0:
                self.airicehorizons_chol = cholesky(self.airicehorizons_correlation)
                self.airicehorizons_lu_piv = lu_factor(self.airicehorizons_chol)


    def residuals(self):
        """Calculate the residual terms of a pair of sites."""

        resi_iceice = (self.site1.fct_age(self.iceicehorizons_depth1)-\
                       self.site2.fct_age(self.iceicehorizons_depth2))/self.iceicehorizons_sigma
        if np.size(self.iceicehorizons_depth1) > 0:
            resi_iceice = lu_solve(self.iceicehorizons_lu_piv, resi_iceice)
        resi = resi_iceice

        if self.site1.archive == 'icecore' and self.site2.archive == 'icecore':
            resi_airair = (self.site1.fct_airage(self.airairhorizons_depth1)-\
                          self.site2.fct_airage(self.airairhorizons_depth2))/\
                          self.airairhorizons_sigma
            if np.size(self.airairhorizons_depth1) > 0:
                resi_airair = lu_solve(self.airairhorizons_lu_piv, resi_airair)
            resi = np.concatenate((resi, resi_airair))

        if self.site2.archive == 'icecore':
            resi_iceair = (self.site1.fct_age(self.iceairhorizons_depth1)-\
                          self.site2.fct_airage(self.iceairhorizons_depth2))/\
                          self.iceairhorizons_sigma
            if np.size(self.iceairhorizons_depth1) > 0:
                resi_iceair = lu_solve(self.iceairhorizons_lu_piv, resi_iceair)
            resi = np.concatenate((resi, resi_iceair))

        if self.site1.archive == 'icecore':
            resi_airice = (self.site1.fct_airage(self.airicehorizons_depth1)-\
                           self.site2.fct_age(self.airicehorizons_depth2))/self.airicehorizons_sigma
            if np.size(self.airicehorizons_depth1) > 0:
                resi_airice = lu_solve(self.airicehorizons_lu_piv, resi_airice)
                resi = np.concatenate((resi, resi_airice))

        return resi


    def figures(self):
        """Build the figures related to a pair of sites."""

        if not os.path.isdir(pccfg.DATADIR+self.label):
            os.mkdir(pccfg.DATADIR+self.label)


        mpl.figure(self.label+' main-main')
        if self.site1.archive == 'icecore':
            mpl.xlabel(self.site1.label+' ice age (yr b1950)')
        else:
            mpl.xlabel(self.site1.label+' age (yr b1950)')
        if self.site2.archive == 'icecore':
            mpl.ylabel(self.site2.label+' ice age (yr b1950)')
        else:
            mpl.ylabel(self.site2.label+' age (yr b1950)')
        if np.size(self.iceicehorizons_depth1) > 0:
            if pccfg.SHOW_INITIAL:
                mpl.errorbar(self.site1.fct_age_init(self.iceicehorizons_depth1),
                             self.site2.fct_age_init(self.iceicehorizons_depth2),
                             color=pccfg.COLOR_INIT,
                             xerr=self.iceicehorizons_sigma, linestyle='', marker='o', markersize=2,
                             label="Initial")
            mpl.errorbar(self.site1.fct_age_model(self.iceicehorizons_depth1),
                         self.site2.fct_age_model(self.iceicehorizons_depth2),
                         color=pccfg.COLOR_MOD,
                         xerr=self.iceicehorizons_sigma, linestyle='', marker='o', markersize=2,
                         label="Prior")
            mpl.errorbar(self.site1.fct_age(self.iceicehorizons_depth1),
                         self.site2.fct_age(self.iceicehorizons_depth2), color=pccfg.COLOR_OPT,
                         xerr=self.iceicehorizons_sigma, linestyle='', marker='o', markersize=2,
                         label="Posterior")
        x_low, x_up, y_low, y_up = mpl.axis()
        x_low = self.site1.age_top
        y_low = self.site2.age_top
        mpl.axis((x_low, x_up, y_low, y_up))
        rangefig = np.array([max(x_low, y_low), min(x_up, y_up)])
        mpl.plot(rangefig, rangefig, color=pccfg.COLOR_OBS, label='perfect agreement')
        mpl.legend(loc="best")
        if self.site1.archive == 'icecore' and self.site2.archive == 'icecore':
            printed_page = PdfPages(pccfg.DATADIR+self.label+'/ice_ice_synchro.pdf')
        elif self.site1.archive == 'icecore' or self.site2.archive == 'icecore':
            printed_page = PdfPages(pccfg.DATADIR+self.label+'/ice_synchro.pdf')
        else:
            printed_page = PdfPages(pccfg.DATADIR+self.label+'/synchro.pdf')
        printed_page.savefig(mpl.figure(self.label+' main-main'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        if self.site1.archive == 'icecore' and self.site2.archive == 'icecore':
            mpl.figure(self.label+' air-air')
            mpl.xlabel(self.site1.label+' air age (yr b1950)')
            mpl.ylabel(self.site2.label+' air age (yr b1950)')
            if np.size(self.airairhorizons_depth1) > 0:
                if pccfg.SHOW_INITIAL:
                    mpl.errorbar(self.site1.fct_airage_init(self.airairhorizons_depth1),
                                 self.site2.fct_airage_init(self.airairhorizons_depth2),
                                 color=pccfg.COLOR_INIT, xerr=self.airairhorizons_sigma,
                                 linestyle='',
                                 marker='o', markersize=2, label="Initial")
                mpl.errorbar(self.site1.fct_airage_model(self.airairhorizons_depth1),
                             self.site2.fct_airage_model(self.airairhorizons_depth2),
                             color=pccfg.COLOR_MOD,
                             xerr=self.airairhorizons_sigma, linestyle='', marker='o', markersize=2,
                             label="Prior")
                mpl.errorbar(self.site1.fct_airage(self.airairhorizons_depth1),
                             self.site2.fct_airage(self.airairhorizons_depth2),
                             color=pccfg.COLOR_OPT,
                             xerr=self.airairhorizons_sigma, linestyle='', marker='o', markersize=2,
                             label="Posterior")
            x_low, x_up, y_low, y_up = mpl.axis()
            x_low = self.site1.age_top
            y_low = self.site2.age_top
            mpl.axis((x_low, x_up, y_low, y_up))
            rangefig = np.array([max(x_low, y_low), min(x_up, y_up)])
            mpl.plot(rangefig, rangefig, color=pccfg.COLOR_OBS, label='perfect agreement')
            mpl.legend(loc="best")
            printed_page = PdfPages(pccfg.DATADIR+self.label+'/air_air_synchro.pdf')
            printed_page.savefig(mpl.figure(self.label+' air-air'))
            printed_page.close()
            if not pccfg.SHOW_FIGURES:
                mpl.close()

        if self.site2.archive == 'icecore':
            mpl.figure(self.label+' main-air')
            if self.site1.archive == 'icecore':
                mpl.xlabel(self.site1.label+' ice age (yr b1950)')
            else:
                mpl.xlabel(self.site1.label+' age (yr b1950)')
            mpl.ylabel(self.site2.label+' air age (yr b1950)')
            if np.size(self.iceairhorizons_depth1) > 0:
                if pccfg.SHOW_INITIAL:
                    mpl.errorbar(self.site1.fct_age_init(self.iceairhorizons_depth1),
                                 self.site2.fct_airage_init(self.iceairhorizons_depth2),
                                 color=pccfg.COLOR_INIT, xerr=self.iceairhorizons_sigma,
                                 linestyle='',
                                 marker='o', markersize=2, label="Initial")
                mpl.errorbar(self.site1.fct_age_model(self.iceairhorizons_depth1),
                             self.site2.fct_airage_model(self.iceairhorizons_depth2),
                             color=pccfg.COLOR_MOD,
                             xerr=self.iceairhorizons_sigma, linestyle='', marker='o', markersize=2,
                             label="Prior")
                mpl.errorbar(self.site1.fct_age(self.iceairhorizons_depth1),
                             self.site2.fct_airage(self.iceairhorizons_depth2),
                             color=pccfg.COLOR_OPT,
                             xerr=self.iceairhorizons_sigma, linestyle='', marker='o', markersize=2,
                             label="Posterior")
            x_low, x_up, y_low, y_up = mpl.axis()
            x_low = self.site1.age_top
            y_low = self.site2.age_top
            mpl.axis((x_low, x_up, y_low, y_up))
            rangefig = np.array([max(x_low, y_low), min(x_up, y_up)])
            mpl.plot(rangefig, rangefig, color=pccfg.COLOR_OBS, label='perfect agreement')
            mpl.legend(loc="best")
            if self.site1.archive == 'icecore':
                printed_page = PdfPages(pccfg.DATADIR+self.label+'/ice_air_synchro.pdf')
            else:
                printed_page = PdfPages(pccfg.DATADIR+self.label+'/air_synchro.pdf')
            printed_page.savefig(mpl.figure(self.label+' main-air'))
            printed_page.close()
            if not pccfg.SHOW_FIGURES:
                mpl.close()

        if self.site1.archive == 'icecore':
            mpl.figure(self.label+' air-main')
            mpl.xlabel(self.site1.label+' air age (yr b1950)')
            if self.site2.archive == 'icecore':
                mpl.ylabel(self.site2.label+' ice age (yr b1950)')
            else:
                mpl.ylabel(self.site2.label+' age (yr b1950)')
            if np.size(self.airicehorizons_depth1) > 0:
                if pccfg.SHOW_INITIAL:
                    mpl.errorbar(self.site1.fct_airage_init(self.airicehorizons_depth1),
                                 self.site2.fct_age_init(self.airicehorizons_depth2),
                                 color=pccfg.COLOR_INIT, xerr=self.airicehorizons_sigma,
                                 linestyle='', marker='o', markersize=2, label="Initial")
                mpl.errorbar(self.site1.fct_airage_model(self.airicehorizons_depth1),
                             self.site2.fct_age_model(self.airicehorizons_depth2),
                             color=pccfg.COLOR_MOD,
                             xerr=self.airicehorizons_sigma, linestyle='', marker='o', markersize=2,
                             label="Prior")
                mpl.errorbar(self.site1.fct_airage(self.airicehorizons_depth1),
                             self.site2.fct_age(self.airicehorizons_depth2), color=pccfg.COLOR_OPT,
                             xerr=self.airicehorizons_sigma, linestyle='', marker='o', markersize=2,
                             label="Posterior")
            x_low, x_up, y_low, y_up = mpl.axis()
            x_low = self.site1.age_top
            y_low = self.site2.age_top
            mpl.axis((x_low, x_up, y_low, y_up))
            rangefig = np.array([max(x_low, y_low), min(x_up, y_up)])
            mpl.plot(rangefig, rangefig, color=pccfg.COLOR_OBS, label='perfect agreement')
            mpl.legend(loc="best")
            if self.site2.archive == 'icecore':
                printed_page = PdfPages(pccfg.DATADIR+self.label+'/air_ice_synchro.pdf')
            else:
                printed_page = PdfPages(pccfg.DATADIR+self.label+'/air_synchro.pdf')
            printed_page.savefig(mpl.figure(self.label+' air-main'))
            printed_page.close()
            if not pccfg.SHOW_FIGURES:
                mpl.close()
