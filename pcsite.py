#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  7 11:56:06 2019
Module for the Site class.
@author: parrenif
"""

import os
import sys
import warnings
import math as m
import numpy as np
import matplotlib.pyplot as mpl
from matplotlib.backends.backend_pdf import PdfPages
from scipy.linalg import lu_factor, lu_solve
from scipy.linalg import cholesky
from scipy.interpolate import interp1d
from scipy.optimize import leastsq
from pcmath import interp_lin_aver, interp_stair_aver
import pccfg

##dummy use of the interp1d function
interp1d

class Site(object):
    """This is the class for a site."""

    def __init__(self, dlab):
        self.label = dlab

        #Default parameters
        self.archive = 'icecore'
        self.accu_prior_rep = 'staircase'
        self.udepth_top = None
        self.age_top = None
        self.depth = np.empty(0)
        self.corr_a_age = None
        self.calc_a = False
        self.calc_a_method = None
        self.gamma_source = None
        self.beta_source = None
        self.calc_tau = False
        self.thickness = None
        self.calc_lid = False
        self.lid_value = None
        self.start = 'default'
        self.corr_lid_age = None
        self.corr_tau_depth = None
        self.accu0 = None
        self.beta = None
        self.pprime = None
        self.muprime = None
        self.sliding = None
        self.dens_firn = None

        #Setting the parameters from the parameter files
        filename = pccfg.DATADIR+'/parameters-AllSites.py'
        if os.path.isfile(filename):
            execfile(filename)
        else:
            filename = pccfg.DATADIR+'/parameters-AllDrillings.py'
            if os.path.isfile(filename):
                execfile(filename)
        execfile(pccfg.DATADIR+self.label+'/parameters.py')

        try:
            self.calc_lid = self.calc_LID
        except AttributeError:
            pass
        try:
            self.corr_lid_age = self.corr_LID_age
        except AttributeError:
            pass
        try:
            self.dens_firn = self.Dfirn
        except AttributeError:
            pass
        try:
            self.sliding = self.s
        except AttributeError:
            pass
        try:
            self.accu0 = self.A0
        except AttributeError:
            pass

        ##Initialisation of variables
        self.depth_mid = (self.depth[1:]+self.depth[:-1])/2
        self.depth_inter = (self.depth[1:]-self.depth[:-1])
        self.lid = np.empty_like(self.depth)
        self.sigma_delta_depth = np.empty_like(self.depth)
        self.sigma_airlayerthick = np.empty_like(self.depth_mid)
        self.airlayerthick_init = np.empty_like(self.depth_mid)
        self.age_init = np.empty_like(self.depth)
        self.sigma_accu = np.empty_like(self.depth_mid)
        self.sigma_accu_model = np.empty_like(self.depth_mid)
        self.tau_init = np.empty_like(self.depth_mid)
        self.a_init = np.empty_like(self.depth_mid)
        self.airage_init = np.empty_like(self.depth_mid)
        self.sigma_icelayerthick = np.empty_like(self.depth_mid)
        self.airlayerthick = np.empty_like(self.depth_mid)
        self.ice_equiv_depth = np.empty_like(self.depth)
        self.sigma_tau = np.empty_like(self.depth_mid)
        self.icelayerthick = np.empty_like(self.depth_mid)
        self.icelayerthick_init = np.empty_like(self.depth_mid)
        self.sigma_tau_model = np.empty_like(self.depth_mid)
        self.delta_depth_init = np.empty_like(self.depth)
        self.sigma_lid_model = np.empty_like(self.depth)
        self.lid_init = np.empty_like(self.depth)
        self.sigma_age = np.empty_like(self.depth)
        self.sigma_airage = np.empty_like(self.depth)
        self.lidie = np.empty_like(self.depth)
        self.sigma_lid = np.empty_like(self.depth)
        self.ulidie = np.empty_like(self.depth)
        self.hess = np.array([])

## We set up the raw model
        if self.calc_a:
            readarray = np.loadtxt(pccfg.DATADIR+self.label+'/isotopes.txt')
            if np.size(readarray) == np.shape(readarray)[0]:
                readarray.resize(1, np.size(readarray))
            self.iso_depth = readarray[:, 0]
            if self.calc_a_method == 'fullcorr':
                self.iso_d18o_ice = readarray[:, 1]
                self.d18o_ice = interp_stair_aver(self.depth, self.iso_depth, self.iso_d18o_ice)
                self.iso_deutice = readarray[:, 2]
                self.deutice = interp_stair_aver(self.depth, self.iso_depth, self.iso_deutice)
                self.iso_d18o_sw = readarray[:, 3]
                self.d18o_sw = interp_stair_aver(self.depth, self.iso_depth, self.iso_d18o_sw)
                self.excess = self.deutice-8*self.d18o_ice   # dans Uemura : d=excess
                self.accu = np.empty_like(self.deutice)
                self.d18o_ice_corr = self.d18o_ice-self.d18o_sw*(1+self.d18o_ice/1000)/\
                    (1+self.d18o_sw/1000)	#Uemura (1)
                self.deutice_corr = self.deutice-8*self.d18o_sw*(1+self.deutice/1000)/\
                    (1+8*self.d18o_sw/1000) #Uemura et al. (CP, 2012) (2)
                self.excess_corr = self.deutice_corr-8*self.d18o_ice_corr
                self.deutice_fullcorr = self.deutice_corr+self.gamma_source/self.beta_source*\
                    self.excess_corr
            elif self.calc_a_method == 'deut':
                self.iso_deutice = readarray[:, 1]
                self.deutice_fullcorr = interp_stair_aver(self.depth, self.iso_depth,
                                                          self.iso_deutice)
            elif self.calc_a_method == 'd18O':
                self.d18o_ice = readarray[:, 1]
                self.deutice_fullcorr = 8*interp_stair_aver(self.depth, self.iso_depth,
                                                            self.iso_d18o_ice)
            else:
                print 'Accumulation method not recognized'
                sys.exit()
        else:
            readarray = np.loadtxt(pccfg.DATADIR+self.label+'/accu-prior.txt')
            if np.size(readarray) == np.shape(readarray)[0]:
                readarray.resize(1, np.size(readarray))
            self.a_depth = readarray[:, 0]
            self.a_a = readarray[:, 1]
            if readarray.shape[1] >= 3:
                self.a_sigma = readarray[:, 2]
            if self.accu_prior_rep == 'staircase':
                self.a_model = interp_stair_aver(self.depth, self.a_depth, self.a_a)
            elif self.accu_prior_rep == 'linear':
                self.a_model = interp_lin_aver(self.depth, self.a_depth, self.a_a)
            else:
                print 'Representation of prior accu scenario not recognized'
            self.accu = self.a_model

        self.age = np.empty_like(self.depth)
        self.airage = np.empty_like(self.depth)

        if self.archive == 'icecore':

            readarray = np.loadtxt(pccfg.DATADIR+self.label+'/density-prior.txt')
            #        self.density_depth=readarray[:,0]
            if np.size(readarray) == np.shape(readarray)[0]:
                readarray.resize(1, np.size(readarray))
            self.dens_depth = readarray[:, 0]
            self.dens_dens = readarray[:, 1]
            self.dens = np.interp(self.depth_mid, self.dens_depth, self.dens_dens)
            self.iedepth = np.cumsum(np.concatenate((np.array([0]), self.dens*self.depth_inter)))
            self.iedepth_mid = (self.iedepth[1:]+self.iedepth[:-1])/2

            if self.calc_tau:
                self.thickness_ie = self.thickness-self.depth[-1]+self.iedepth[-1]

            if self.calc_lid:
                if self.depth[0] < self.lid_value:
                    self.lid_depth = np.array([self.depth[0], self.lid_value, self.depth[-1]])
                    self.lid_lid = np.array([self.depth[0], self.lid_value, self.lid_value])
                else:
                    self.lid_depth = np.array([self.depth[0], self.depth[-1]])
                    self.lid_lid = np.array([self.lid_value, self.lid_value])
            else:
    #            self.lid_model=np.loadtxt(pccfg.DATADIR+self.label+'/LID-prior.txt')
                readarray = np.loadtxt(pccfg.DATADIR+self.label+'/LID-prior.txt')
                if np.size(readarray) == np.shape(readarray)[0]:
                    readarray.resize(1, np.size(readarray))
                self.lid_depth = readarray[:, 0]
                self.lid_lid = readarray[:, 1]
                if readarray.shape[1] >= 3:
                    self.lid_sigma = readarray[:, 2]
            self.lid_model = np.interp(self.depth, self.lid_depth, self.lid_lid)

            self.delta_depth = np.empty_like(self.depth)
            self.udepth = np.empty_like(self.depth)

#        print 'depth_mid ', np.size(self.depth_mid)
#        print 'zeta ', np.size(self.zeta)
            if self.calc_tau:
                self.thicknessie = self.thickness-self.depth[-1]+self.iedepth[-1]
                #FIXME: maybe we should use iedepth and thickness_ie here?
                self.zeta = (self.thicknessie-self.iedepth_mid)/self.thicknessie
                self.tau = np.empty_like(self.depth_mid)
            else:
                readarray = np.loadtxt(pccfg.DATADIR+self.label+'/thinning-prior.txt')
                if np.size(readarray) == np.shape(readarray)[0]:
                    readarray.resize(1, np.size(readarray))
                self.tau_depth = readarray[:, 0]
                self.tau_tau = readarray[:, 1]
                if readarray.shape[1] >= 3:
                    self.tau_sigma = readarray[:, 2]
                self.tau_model = np.interp(self.depth_mid, self.tau_depth, self.tau_tau)
                self.tau = self.tau_model

        self.raw_model()

## Now we set up the correction functions

        if self.start == 'restart':
            self.variables = np.loadtxt(pccfg.DATADIR+self.label+'/restart.txt')
        elif self.start == 'default':
            self.corr_a = np.zeros(np.size(self.corr_a_age))
            if self.archive == 'icecore':
                self.corr_lid = np.zeros(np.size(self.corr_lid_age))
                self.corr_tau = np.zeros(np.size(self.corr_tau_depth))
        elif self.start == 'random':
            self.corr_a = np.random.normal(loc=0., scale=1., size=np.size(self.corr_a_age))
            if self.archive == 'icecore':
                self.corr_lid = np.random.normal(loc=0., scale=1., size=np.size(self.corr_lid_age))
                self.corr_tau = np.random.normal(loc=0., scale=1.,
                                                 size=np.size(self.corr_tau_depth))
        else:
            print 'Start option not recognized.'

## Now we set up the correlation matrices

        self.correlation_corr_a = np.diag(np.ones(np.size(self.corr_a)))
        self.chol_a = np.diag(np.ones(np.size(self.corr_a)))
        if self.archive == 'icecore':
            self.correlation_corr_lid = np.diag(np.ones(np.size(self.corr_lid)))
            self.correlation_corr_tau = np.diag(np.ones(np.size(self.corr_tau)))
            self.chol_lid = np.diag(np.ones(np.size(self.corr_lid)))
            self.chol_tau = np.diag(np.ones(np.size(self.corr_tau)))



## Definition of the covariance matrix of the background

        try:
            #FIXME: we should average here since it would be more representative
            self.sigmap_corr_a = np.interp(self.corr_a_age, self.fct_age_model(self.a_depth),
                                           self.a_sigma)
        except AttributeError:
            print 'Sigma on prior accu scenario not defined in the accu-prior.txt file'

        if self.archive == 'icecore':
            try:
                 #FIXME: we should average here since it would be more representative
                self.sigmap_corr_lid = np.interp(self.corr_lid_age,
                                                 self.fct_airage_model(self.lid_depth),
                                                 self.lid_sigma)
            except AttributeError:
                print 'Sigma on prior LID scenario not defined in the LID-prior.txt file'

            try:
                #FIXME: we should average here since it would be more representative
                self.sigmap_corr_tau = np.interp(self.corr_tau_depth, self.tau_depth,
                                                 self.tau_sigma)
            except AttributeError:
                print 'Sigma on prior thinning scenario not defined in the thinning-prior.txt file'

        self.correlation_corr_a_before = self.correlation_corr_a+0
        if self.archive == 'icecore':
            self.correlation_corr_lid_before = self.correlation_corr_lid+0
            self.correlation_corr_tau_before = self.correlation_corr_tau+0

        filename = pccfg.DATADIR+self.label+'/parameters-CovariancePrior-init.py'
        if os.path.isfile(filename):
            execfile(filename)
        else:
            filename = pccfg.DATADIR+'/parameters-CovariancePrior-AllSites-init.py'
            if os.path.isfile(filename):
                execfile(filename)
            else:
                filename = pccfg.DATADIR+'/parameters-CovariancePrior-AllDrillings-init.py'
                if os.path.isfile(filename):
                    execfile(filename)


        if (self.correlation_corr_a_before != self.correlation_corr_a).any():
            self.chol_a = cholesky(self.correlation_corr_a)
        if self.archive == 'icecore':
            if (self.correlation_corr_lid_before != self.correlation_corr_lid).any():
                self.chol_lid = cholesky(self.correlation_corr_lid)
            if (self.correlation_corr_a_before != self.correlation_corr_a).any():
                self.chol_tau = cholesky(self.correlation_corr_tau)


        self.variables = np.array([])
#        if self.calc_a==True:
#            self.variables=np.concatenate((self.variables, np.array([self.accu0]),
#                                           np.array([self.beta])))
#        if self.calc_tau==True:
#            self.variables=np.concatenate((self.variables, np.array([self.pprime]),
#                                           np.array([self.muprime])))
        self.variables = np.concatenate((self.variables, self.corr_tau, self.corr_a, self.corr_lid))


#Reading of observations

        if self.archive == 'icecore':
            filename = pccfg.DATADIR+self.label+'/ice_age.txt'
        else:
            filename = pccfg.DATADIR+self.label+'/age.txt'
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if os.path.isfile(filename) and open(filename).read() and\
                np.size(np.loadtxt(filename)) > 0:
                readarray = np.loadtxt(filename)
                if np.size(readarray) == np.shape(readarray)[0]:
                    readarray.resize(1, np.size(readarray))
                self.icemarkers_depth = readarray[:, 0]
                self.icemarkers_age = readarray[:, 1]
                self.icemarkers_sigma = readarray[:, 2]
            else:
                self.icemarkers_depth = np.array([])
                self.icemarkers_age = np.array([])
                self.icemarkers_sigma = np.array([])

        if self.archive == 'icecore':
            filename = pccfg.DATADIR+self.label+'/ice_age_intervals.txt'
        else:
            filename = pccfg.DATADIR+self.label+'/age_intervals.txt'
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if os.path.isfile(filename) and open(filename).read() and\
                np.size(np.loadtxt(filename)) > 0:
                readarray = np.loadtxt(filename)
                if np.size(readarray) == np.shape(readarray)[0]:
                    readarray.resize(1, np.size(readarray))
                self.iceintervals_depthtop = readarray[:, 0]
                self.iceintervals_depthbot = readarray[:, 1]
                self.iceintervals_duration = readarray[:, 2]
                self.iceintervals_sigma = readarray[:, 3]
            else:
                self.iceintervals_depthtop = np.array([])
                self.iceintervals_depthbot = np.array([])
                self.iceintervals_duration = np.array([])
                self.iceintervals_sigma = np.array([])

        if self.archive == 'icecore':
            filename = pccfg.DATADIR+self.label+'/air_age.txt'
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if os.path.isfile(filename) and open(filename).read() and\
                    np.size(np.loadtxt(filename)) > 0:
                    readarray = np.loadtxt(filename)
                    if np.size(readarray) == np.shape(readarray)[0]:
                        readarray.resize(1, np.size(readarray))
                    self.airmarkers_depth = readarray[:, 0]
                    self.airmarkers_age = readarray[:, 1]
                    self.airmarkers_sigma = readarray[:, 2]
                else:
                    self.airmarkers_depth = np.array([])
                    self.airmarkers_age = np.array([])
                    self.airmarkers_sigma = np.array([])

            filename = pccfg.DATADIR+self.label+'/air_age_intervals.txt'
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if os.path.isfile(filename) and open(filename).read() and\
                    np.size(np.loadtxt(filename)) > 0:
                    readarray = np.loadtxt(filename)
                    if np.size(readarray) == np.shape(readarray)[0]:
                        readarray.resize(1, np.size(readarray))
                    self.airintervals_depthtop = readarray[:, 0]
                    self.airintervals_depthbot = readarray[:, 1]
                    self.airintervals_duration = readarray[:, 2]
                    self.airintervals_sigma = readarray[:, 3]
                else:
                    self.airintervals_depthtop = np.array([])
                    self.airintervals_depthbot = np.array([])
                    self.airintervals_duration = np.array([])
                    self.airintervals_sigma = np.array([])

            filename = pccfg.DATADIR+self.label+'/Ddepth.txt'
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if os.path.isfile(filename) and open(filename).read() and\
                    np.size(np.loadtxt(filename)) > 0:
                    readarray = np.loadtxt(filename)
                    if np.size(readarray) == np.shape(readarray)[0]:
                        readarray.resize(1, np.size(readarray))
                    self.delta_depth_depth = readarray[:, 0]
                    self.delta_depth_delta_depth = readarray[:, 1]
                    self.delta_depth_sigma = readarray[:, 2]
                else:
                    self.delta_depth_depth = np.array([])
                    self.delta_depth_delta_depth = np.array([])
                    self.delta_depth_sigma = np.array([])


        self.icemarkers_correlation = np.diag(np.ones(np.size(self.icemarkers_depth)))
        self.iceintervals_correlation = np.diag(np.ones(np.size(self.iceintervals_depthtop)))
        if self.archive == 'icecore':
            self.airmarkers_correlation = np.diag(np.ones(np.size(self.airmarkers_depth)))
            self.airintervals_correlation = np.diag(np.ones(np.size(self.airintervals_depthtop)))
            self.delta_depth_correlation = np.diag(np.ones(np.size(self.delta_depth_depth)))
#        print self.icemarkers_correlation

        filename = pccfg.DATADIR+'/parameters-CovarianceObservations-AllSites.py'
        if os.path.isfile(filename):
            execfile(filename)
        else:
            filename = pccfg.DATADIR+'/parameters-CovarianceObservations-AllDrillings.py'
            if os.path.isfile(filename):
                execfile(filename)

        filename = pccfg.DATADIR+self.label+'/parameters-CovarianceObservations.py'
        if os.path.isfile(filename):
            execfile(filename)
        if np.size(self.icemarkers_depth) > 0:
            self.icemarkers_chol = cholesky(self.icemarkers_correlation)
            #FIXME: we LU factor a triangular matrix. This is suboptimal.
            #We should set lu_piv directly instead.
            self.icemarkers_lu_piv = lu_factor(np.transpose(self.icemarkers_chol))
        if np.size(self.iceintervals_depthtop) > 0:
            self.iceintervals_chol = cholesky(self.iceintervals_correlation)
            self.iceintervals_lu_piv = lu_factor(np.transpose(self.iceintervals_chol))
        if self.archive == 'icecore':
            if np.size(self.airmarkers_depth) > 0:
                self.airmarkers_chol = cholesky(self.airmarkers_correlation)
                self.airmarkers_lu_piv = lu_factor(np.transpose(self.airmarkers_chol))
            if np.size(self.airintervals_depthtop) > 0:
                self.airintervals_chol = cholesky(self.airintervals_correlation)
                self.airintervals_lu_piv = lu_factor(np.transpose(self.airintervals_chol))
            if np.size(self.delta_depth_depth) > 0:
                self.delta_depth_chol = cholesky(self.delta_depth_correlation)
                self.delta_depth_lu_piv = lu_factor(np.transpose(self.delta_depth_chol))

    def raw_model(self):
        """Calculate the raw model, that is before applying correction functions."""

        if self.archive == 'icecore':
            #Accumulation
            if self.calc_a:
                self.a_model = self.accu0*np.exp(self.beta*(self.deutice_fullcorr-\
                    self.deutice_fullcorr[0])) #Parrenin et al. (CP, 2007a) 2.3 (6)
    
            #Thinning
            if self.calc_tau:
                self.p_def = -1+m.exp(self.pprime)
                self.mu_melt = m.exp(self.muprime)
    #            self.sliding=m.tanh(self.sprime)
                #Parrenin et al. (CP, 2007a) 2.2 (3)
                omega_def = 1-(self.p_def+2)/(self.p_def+1)*(1-self.zeta)+\
                          1/(self.p_def+1)*(1-self.zeta)**(self.p_def+2)
                #Parrenin et al. (CP, 2007a) 2.2 (2)
                omega = self.sliding*self.zeta+(1-self.sliding)*omega_def
                self.tau_model = (1-self.mu_melt)*omega+self.mu_melt
    
            #udepth
            self.udepth_model = self.udepth_top+np.cumsum(np.concatenate((np.array([0]),\
                                self.dens/self.tau_model*self.depth_inter)))
    
            self.lidie_model = self.lid_model*self.dens_firn
            self.ulidie_model = np.interp(self.lidie_model, self.iedepth, self.udepth_model)

        #Ice age
        if self.archive == 'icecore':
            self.icelayerthick_model = self.tau_model*self.a_model/self.dens
        else:
            self.icelayerthick = self.a_model
        self.age_model = self.age_top+np.cumsum(np.concatenate((np.array([0]),\
                         self.depth_inter/self.icelayerthick_model)))

        #air age
        if self.archive =='icecore':
            self.ice_equiv_depth_model = np.interp(self.udepth_model-self.ulidie_model,
                                                   self.udepth_model, self.depth)
            self.delta_depth_model = self.depth-self.ice_equiv_depth_model
            self.airage_model = np.interp(self.ice_equiv_depth_model, self.depth, self.age_model,
                                          left=np.nan, right=np.nan)
            self.airlayerthick_model = 1/np.diff(self.airage_model)

    def corrected_model(self):
        """Calculate the age model, taking into account the correction functions."""

        self.correlation_corr_a_before = self.correlation_corr_a+0
        if self.archive == 'icecore':
            self.correlation_corr_lid_before = self.correlation_corr_lid+0
            self.correlation_corr_tau_before = self.correlation_corr_tau+0

        filename = pccfg.DATADIR+'/parameters-CovariancePrior-AllSites.py'
        if os.path.isfile(filename):
            execfile(filename)
        filename = pccfg.DATADIR+self.label+'/parameters-CovariancePrior.py'
        if os.path.isfile(filename):
            execfile(filename)

        if (self.correlation_corr_a_before != self.correlation_corr_a).any():
            self.chol_a = cholesky(self.correlation_corr_a)
        if self.archive == 'icecore':
            if (self.correlation_corr_lid_before != self.correlation_corr_lid).any():
                self.chol_lid = cholesky(self.correlation_corr_lid)
            if (self.correlation_corr_a_before != self.correlation_corr_a).any():
                self.chol_tau = cholesky(self.correlation_corr_tau)

        #Accu
        corr = np.dot(self.chol_a, self.corr_a)*self.sigmap_corr_a
        #FIXME: we should use mid-age and not age
        self.accu = self.a_model*np.exp(np.interp(self.age_model[:-1], self.corr_a_age, corr))

        #Thinning and LID
        if self.archive == 'icecore':
            self.tau = self.tau_model*np.exp(np.interp(self.depth_mid, self.corr_tau_depth,\
                       np.dot(self.chol_tau, self.corr_tau)*self.sigmap_corr_tau))
            self.udepth = self.udepth_top+np.cumsum(np.concatenate((np.array([0]),\
                          self.dens/self.tau*self.depth_inter)))
            corr = np.dot(self.chol_lid, self.corr_lid)*self.sigmap_corr_lid
            self.lid = self.lid_model*np.exp(np.interp(self.age_model, self.corr_lid_age, corr))
            self.lidie = self.lid*self.dens_firn
            self.ulidie = np.interp(self.lidie, self.iedepth, self.udepth)

        #Ice age
        if self.archive == 'icecore':
            self.icelayerthick = self.tau*self.accu/self.dens
        else:
            self.icelayerthick = self.accu
        self.age = self.age_top+np.cumsum(np.concatenate((np.array([0]),\
                   self.depth_inter/self.icelayerthick)))

        #Air age
        if self.archive == 'icecore':
            self.ice_equiv_depth = np.interp(self.udepth-self.ulidie, self.udepth, self.depth)
            self.delta_depth = self.depth-self.ice_equiv_depth
            self.airage = np.interp(self.ice_equiv_depth, self.depth, self.age, left=np.nan,
                                    right=np.nan)
            self.airlayerthick = 1/np.diff(self.airage)

    def model(self, var):
        """Calculate the model from the vector var containing its variables."""
        index = 0
#        if self.calc_a==True:
#            self.accu0=var[index]
#            self.beta=var[index+1]
#            index=index+2
#        if self.calc_tau==True:
##            self.p_def=-1+m.exp(var[index])
##            self.sliding=var[index+1]
##            self.mu_melt=var[index+2]
##            index=index+3
#            self.pprime=var[index]
#            self.muprime=var[index+1]
#            index=index+2
        self.corr_tau = var[index:index+np.size(self.corr_tau)]
        self.corr_a = var[index+np.size(self.corr_tau):\
                          index+np.size(self.corr_tau)+np.size(self.corr_a)]
        self.corr_lid = var[index+np.size(self.corr_tau)+np.size(self.corr_a):\
                        index+np.size(self.corr_tau)+np.size(self.corr_a)+np.size(self.corr_lid)]

        ##Raw model
        self.raw_model()

        ##Corrected model
        self.corrected_model()

        return np.concatenate((self.age, self.airage, self.delta_depth, self.accu, self.tau,
                               self.lid, self.icelayerthick, self.airlayerthick))


    def write_init(self):
        """Write the initial values of the variables in the corresponding *_init variables."""
        self.a_init = self.accu
        self.lid_init = self.lid
        self.tau_init = self.tau
        self.icelayerthick_init = self.icelayerthick
        self.airlayerthick_init = self.airlayerthick
        self.age_init = self.age
        self.airage_init = self.airage
        self.delta_depth_init = self.delta_depth

    def fct_age(self, depth):
        """Return the age at given depths."""
        return np.interp(depth, self.depth, self.age)

    def fct_age_init(self, depth):
        """Return the initial age at given depths."""
        return np.interp(depth, self.depth, self.age_init)

    def fct_age_model(self, depth):
        """Return the raw modelled age at given depths."""
        return np.interp(depth, self.depth, self.age_model)

    def fct_airage(self, depth):
        """Return the air age at given depths."""
        return np.interp(depth, self.depth, self.airage)

    def fct_airage_init(self, depth):
        """Return the initial air age at given depth."""
        return np.interp(depth, self.depth, self.airage_init)

    def fct_airage_model(self, depth):
        """Return the raw modelled air age at given depths."""
        return np.interp(depth, self.depth, self.airage_model)

    def fct_delta_depth(self, depth):
        """Return the delta_depth at given detphs."""
        return np.interp(depth, self.depth, self.delta_depth)

    def residuals(self, var):
        """Calculate the residuals from the vector of the variables"""
        self.model(var)
        resi_corr_a = self.corr_a
        resi_corr_lid = self.corr_lid
        resi_corr_tau = self.corr_tau
        resi_age = (self.fct_age(self.icemarkers_depth)-self.icemarkers_age)/self.icemarkers_sigma
        if np.size(self.icemarkers_depth) > 0:
            resi_age = lu_solve(self.icemarkers_lu_piv, resi_age)
        resi_airage = (self.fct_airage(self.airmarkers_depth)-self.airmarkers_age)/\
                      self.airmarkers_sigma
        if np.size(self.airmarkers_depth) > 0:
            resi_airage = lu_solve(self.airmarkers_lu_piv, resi_airage)
        resi_iceint = (self.fct_age(self.iceintervals_depthbot)-\
                      self.fct_age(self.iceintervals_depthtop)-\
                      self.iceintervals_duration)/self.iceintervals_sigma
        if np.size(self.iceintervals_depthtop) > 0:
            resi_iceint = lu_solve(self.iceintervals_lu_piv, resi_iceint)
        resi_airint = (self.fct_airage(self.airintervals_depthbot)-\
                       self.fct_airage(self.airintervals_depthtop)-\
                       self.airintervals_duration)/self.airintervals_sigma
        if np.size(self.airintervals_depthtop) > 0:
            resi_airint = lu_solve(self.airintervals_lu_piv, resi_airint)
        resi_delta_depth = (self.fct_delta_depth(self.delta_depth_depth)-\
                            self.delta_depth_delta_depth)/self.delta_depth_sigma
        if np.size(self.delta_depth_depth) > 0:
            resi_delta_depth = lu_solve(self.delta_depth_lu_piv, resi_delta_depth)
        return np.concatenate((resi_corr_a, resi_corr_lid, resi_corr_tau, resi_age, resi_airage,
                               resi_iceint, resi_airint, resi_delta_depth))

    def cost_function(self):
        """Calculate the cost function."""
        cost = np.dot(self.residuals, np.transpose(self.residuals))
        return cost

    def jacobian(self):
        """Calculate the jacobian."""
        epsilon = np.sqrt(np.diag(self.hess))/100000000.
        model0 = self.model(self.variables)
        jacob = np.empty((np.size(model0), np.size(self.variables)))
        for i in np.arange(np.size(self.variables)):
            var = self.variables+0
            var[i] = var[i]+epsilon[i]
            model1 = self.model(var)
            jacob[:, i] = (model1-model0)/epsilon[i]
        model0 = self.model(self.variables)
        return jacob

    def optimisation(self):
        """Optimize a site."""
        self.variables, self.hess = leastsq(self.residuals, self.variables, full_output=1)
        print self.variables
        print self.hess
        return self.variables, self.hess

    def sigma(self):
        """Calculate the error of various variables."""
        jacob = self.jacobian()

        index = 0
        c_model = np.dot(jacob[index:index+np.size(self.age), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.age), :])))
        self.sigma_age = np.sqrt(np.diag(c_model))
        index = index+np.size(self.age)
        c_model = np.dot(jacob[index:index+np.size(self.airage), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.airage), :])))
        self.sigma_airage = np.sqrt(np.diag(c_model))
        index = index+np.size(self.airage)
        c_model = np.dot(jacob[index:index+np.size(self.delta_depth), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.delta_depth), :])))
        self.sigma_delta_depth = np.sqrt(np.diag(c_model))
        index = index+np.size(self.delta_depth)
        c_model = np.dot(jacob[index:index+np.size(self.accu), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.accu), :])))
        self.sigma_accu = np.sqrt(np.diag(c_model))
        index = index+np.size(self.accu)
        c_model = np.dot(jacob[index:index+np.size(self.tau), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.tau), :])))
        self.sigma_tau = np.sqrt(np.diag(c_model))
        index = index+np.size(self.tau)
        c_model = np.dot(jacob[index:index+np.size(self.lid), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.lid), :])))
        self.sigma_lid = np.sqrt(np.diag(c_model))
        index = index+np.size(self.lid)
        c_model = np.dot(jacob[index:index+np.size(self.icelayerthick), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.icelayerthick), :])))
        self.sigma_icelayerthick = np.sqrt(np.diag(c_model))
        index = index+np.size(self.icelayerthick)
        c_model = np.dot(jacob[index:index+np.size(self.airlayerthick), :], np.dot(self.hess,\
                               np.transpose(jacob[index:index+np.size(self.airlayerthick), :])))
        self.sigma_airlayerthick = np.sqrt(np.diag(c_model))


        self.sigma_accu_model = np.interp((self.age_model[1:]+self.age_model[:-1])/2,
                                          self.corr_a_age,
                                          self.sigmap_corr_a)
        self.sigma_lid_model = np.interp(self.age_model, self.corr_lid_age, self.sigmap_corr_lid)
        self.sigma_tau_model = np.interp(self.depth_mid, self.corr_tau_depth, self.sigmap_corr_tau)

    def sigma_zero(self):
        """Return zero as the error of various variables."""

        self.sigma_age = np.zeros_like(self.age)
        self.sigma_airage = np.zeros_like(self.airage)
        self.sigma_delta_depth = np.zeros_like(self.delta_depth)
        self.sigma_accu = np.zeros_like(self.accu)
        self.sigma_tau = np.zeros_like(self.tau)
        self.sigma_lid = np.zeros_like(self.lid)
        self.sigma_icelayerthick = np.zeros_like(self.icelayerthick)
        self.sigma_airlayerthick = np.zeros_like(self.airlayerthick)
        self.sigma_accu_model = np.interp((self.age_model[1:]+self.age_model[:-1])/2,
                                          self.corr_a_age,
                                          self.sigmap_corr_a)
        self.sigma_lid_model = np.interp(self.age_model, self.corr_lid_age, self.sigmap_corr_lid)
        self.sigma_tau_model = np.interp(self.depth_mid, self.corr_tau_depth, self.sigmap_corr_tau)





    def figures(self):
        """Build the figures of a site."""

        mpl.figure(self.label+' thinning')
        mpl.title(self.label+' thinning')
        mpl.xlabel('Thinning')
        mpl.ylabel('Depth')
        if pccfg.SHOW_INITIAL:
            mpl.plot(self.tau_init, self.depth_mid, color=pccfg.COLOR_INIT, label='Initial')
        mpl.plot(self.tau_model, self.depth_mid, color=pccfg.COLOR_MOD, label='Prior')
        mpl.plot(self.tau, self.depth_mid, color=pccfg.COLOR_OPT, label='Posterior +/-$\sigma$')
        mpl.fill_betweenx(self.depth_mid, self.tau-self.sigma_tau, self.tau+self.sigma_tau,
                          color=pccfg.COLOR_CI)
#        mpl.plot(self.tau+self.sigma_tau, self.depth_mid, color='k', linestyle='-',
#                 label='+/- 1 sigma')
#        mpl.plot(self.tau-self.sigma_tau, self.depth_mid, color='k', linestyle='-')
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((x_low, x_up, self.depth[-1], self.depth[0]))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/thinning.pdf')
        printed_page.savefig(mpl.figure(self.label+' thinning'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        mpl.figure(self.label+' ice layer thickness')
        mpl.title(self.label+' ice layer thickness')
        mpl.xlabel('thickness of annual layers (m/yr)')
        mpl.ylabel('Depth')
        if pccfg.SHOW_INITIAL:
            mpl.plot(self.icelayerthick_init, self.depth_mid, color=pccfg.COLOR_INIT,
                     label='Initial')
#        for i in range(np.size(self.iceintervals_duration)):
#            y_low=self.iceintervals_depthtop[i]
#            y_up=self.iceintervals_depthbot[i]
#            x_low=(y_up-y_low)/(self.iceintervals_duration[i]+self.iceintervals_sigma[i])
#            x_up=(y_up-y_low)/(self.iceintervals_duration[i]-self.iceintervals_sigma[i])
#            yserie=np.array([y_low,y_low,y_up,y_up,y_low])
#            xserie=np.array([x_low,x_up,x_up,x_low,x_low])
#            if i==0:
#                mpl.plot(xserie,yserie, color=pccfg.COLOR_OBS, label="observations")
#            else:
#                mpl.plot(xserie,yserie, color=pccfg.COLOR_OBS)
        mpl.plot(self.icelayerthick_model, self.depth_mid, color=pccfg.COLOR_MOD, label='Prior')
        mpl.plot(self.icelayerthick, self.depth_mid, color=pccfg.COLOR_OPT,
                 label='Posterior +/-$\sigma$')
        mpl.fill_betweenx(self.depth_mid, self.icelayerthick-self.sigma_icelayerthick,
                          self.icelayerthick+self.sigma_icelayerthick, color=pccfg.COLOR_CI)
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((0, x_up, self.depth[-1], self.depth[0]))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/icelayerthick.pdf')
        printed_page.savefig(mpl.figure(self.label+' ice layer thickness'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        mpl.figure(self.label+' air layer thickness')
        mpl.title(self.label+' air layer thickness')
        mpl.xlabel('thickness of annual layers (m/yr)')
        mpl.ylabel('Depth')
        if pccfg.SHOW_INITIAL:
            mpl.plot(self.airlayerthick_init, self.depth_mid, color=pccfg.COLOR_INIT,
                     label='Initial')
#        for i in range(np.size(self.airintervals_duration)):
#            y_low=self.airintervals_depthtop[i]
#            y_up=self.airintervals_depthbot[i]
#            x_low=(y_up-y_low)/(self.airintervals_duration[i]+self.airintervals_sigma[i])
#            x_up=(y_up-y_low)/(self.airintervals_duration[i]-self.airintervals_sigma[i])
#            yserie=np.array([y_low,y_low,y_up,y_up,y_low])
#            xserie=np.array([x_low,x_up,x_up,x_low,x_low])
#            if i==0:
#                mpl.plot(xserie,yserie, color=pccfg.COLOR_OBS, label='observations')
#            else:
#                mpl.plot(xserie,yserie, color=pccfg.COLOR_OBS)
        mpl.plot(self.airlayerthick_model, self.depth_mid, color=pccfg.COLOR_MOD, label='Prior')
        mpl.plot(self.airlayerthick, self.depth_mid, color=pccfg.COLOR_OPT,
                 label='Posterior +/-$\sigma$')
        mpl.fill_betweenx(self.depth_mid, self.airlayerthick-self.sigma_airlayerthick,
                          self.airlayerthick+self.sigma_airlayerthick, color=pccfg.COLOR_CI)
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((0, 2*max(self.icelayerthick), self.depth[-1], self.depth[0]))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/airlayerthick.pdf')
        if pccfg.SHOW_AIRLAYERTHICK:
            #Fixme: buggy line on anaconda
            printed_page.savefig(mpl.figure(self.label+' air layer thickness'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        mpl.figure(self.label+' accumulation')
        mpl.title(self.label+' accumulation')
        mpl.xlabel('Optimized age (yr)')
        mpl.ylabel('Accumulation (m/yr)')
        if pccfg.SHOW_INITIAL:
            mpl.step(self.age, np.concatenate((self.a_init, np.array([self.a_init[-1]]))),
                     color=pccfg.COLOR_INIT, where='post', label='Initial')
        mpl.step(self.age, np.concatenate((self.a_model, np.array([self.a_model[-1]]))),
                 color=pccfg.COLOR_MOD, where='post', label='Prior')
        mpl.step(self.age, np.concatenate((self.accu, np.array([self.accu[-1]]))),
                 color=pccfg.COLOR_OPT,
                 where='post', label='Posterior +/-$\sigma$')
        mpl.fill_between(self.age[:-1], self.accu-self.sigma_accu, self.accu+self.sigma_accu,
                         color=pccfg.COLOR_CI)
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((self.age_top, x_up, y_low, y_up))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/accumulation.pdf')
        printed_page.savefig(mpl.figure(self.label+' accumulation'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        mpl.figure(self.label+' LID')
        mpl.title(self.label+' LID')
        mpl.xlabel('Optimized age (yr)')
        mpl.ylabel('LID')
        if pccfg.SHOW_INITIAL:
            mpl.plot(self.age, self.lid_init, color=pccfg.COLOR_INIT, label='Initial')
        mpl.plot(self.age, self.lid_model, color=pccfg.COLOR_MOD, label='Prior')
        mpl.plot(self.age, self.lid, color=pccfg.COLOR_OPT, label='Posterior +/-$\sigma$')
        mpl.fill_between(self.age, self.lid-self.sigma_lid, self.lid+self.sigma_lid,
                         color=pccfg.COLOR_CI)
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((self.age_top, x_up, y_low, y_up))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/LID.pdf')
        printed_page.savefig(mpl.figure(self.label+' LID'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        mpl.figure(self.label+' ice age')
        mpl.title(self.label+' ice age')
        mpl.xlabel('age (yr b1950)')
        mpl.ylabel('depth (m)')
        if pccfg.SHOW_INITIAL:
            mpl.plot(self.age_init, self.depth, color=pccfg.COLOR_INIT, label='Initial')
        if np.size(self.icemarkers_depth) > 0:
            mpl.errorbar(self.icemarkers_age, self.icemarkers_depth, color=pccfg.COLOR_OBS,
                         xerr=self.icemarkers_sigma, linestyle='', marker='o', markersize=2,
                         label="dated horizons")
#        mpl.ylim(mpl.ylim()[::-1])
        for i in range(np.size(self.iceintervals_duration)):
            y_low = self.iceintervals_depthtop[i]
            y_up = self.iceintervals_depthbot[i]
            x_low = self.fct_age(y_low)
            x_up = x_low+self.iceintervals_duration[i]
            xseries = np.array([x_low, x_up, x_up, x_low, x_low])
            yseries = np.array([y_low, y_low, y_up, y_up, y_low])
            if i == 0:
                mpl.plot(xseries, yseries, color=pccfg.COLOR_DI, label="dated intervals")
                mpl.errorbar(x_up, y_up, color=pccfg.COLOR_DI, xerr=self.iceintervals_sigma[i],
                             capsize=1)
            else:
                mpl.plot(xseries, yseries, color=pccfg.COLOR_DI)
                mpl.errorbar(x_up, y_up, color=pccfg.COLOR_DI, xerr=self.iceintervals_sigma[i],
                             capsize=1)
        mpl.plot(self.age_model, self.depth, color=pccfg.COLOR_MOD, label='Prior')
        mpl.plot(self.age, self.depth, color=pccfg.COLOR_OPT, label='Posterior +/-$\sigma$')
        mpl.fill_betweenx(self.depth, self.age-self.sigma_age, self.age+self.sigma_age,
                          color=pccfg.COLOR_CI)
        mpl.plot(self.sigma_age*pccfg.SCALE_AGECI, self.depth, color=pccfg.COLOR_SIGMA,
                 label='$\sigma$ x'+str(pccfg.SCALE_AGECI))
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((self.age_top, x_up, self.depth[-1], self.depth[0]))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/ice_age.pdf')
        printed_page.savefig(mpl.figure(self.label+' ice age'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        mpl.figure(self.label+' air age')
        mpl.title(self.label+' air age')
        mpl.xlabel('age (yr b1950)')
        mpl.ylabel('depth (m)')
        if pccfg.SHOW_INITIAL:
            mpl.plot(self.airage_init, self.depth, color=pccfg.COLOR_INIT, label='Initial')
        if np.size(self.airmarkers_depth) > 0:
            mpl.errorbar(self.airmarkers_age, self.airmarkers_depth, color=pccfg.COLOR_OBS,
                         xerr=self.airmarkers_sigma, linestyle='', marker='o', markersize=2,
                         label="observations")
#        mpl.ylim(mpl.ylim()[::-1])
        for i in range(np.size(self.airintervals_duration)):
            y_low = self.airintervals_depthtop[i]
            y_up = self.airintervals_depthbot[i]
            x_low = self.fct_airage(y_low)
            x_up = x_low+self.airintervals_duration[i]
            xseries = np.array([x_low, x_up, x_up, x_low, x_low])
            yseries = np.array([y_low, y_low, y_up, y_up, y_low])
            if i == 0:
                mpl.plot(xseries, yseries, color=pccfg.COLOR_DI, label="dated intervals")
                mpl.errorbar(x_up, y_up, color=pccfg.COLOR_DI, xerr=self.airintervals_sigma[i],
                             capsize=1)
            else:
                mpl.plot(xseries, yseries, color=pccfg.COLOR_DI)
                mpl.errorbar(x_up, y_up, color=pccfg.COLOR_DI, xerr=self.airintervals_sigma[i],
                             capsize=1)
        mpl.plot(self.airage_model, self.depth, color=pccfg.COLOR_MOD, label='Prior')
        mpl.fill_betweenx(self.depth, self.airage-self.sigma_airage, self.airage+self.sigma_airage,
                          color=pccfg.COLOR_CI)
        mpl.plot(self.airage, self.depth, color=pccfg.COLOR_OPT, label='Posterior +/-$\sigma$')
        mpl.plot(self.sigma_airage*pccfg.SCALE_AGECI, self.depth, color=pccfg.COLOR_SIGMA,
                 label='$\sigma$ x'+str(pccfg.SCALE_AGECI))
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((self.age_top, x_up, self.depth[-1], self.depth[0]))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/air_age.pdf')
        printed_page.savefig(mpl.figure(self.label+' air age'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()

        mpl.figure(self.label+' delta_depth')
        mpl.title(self.label+' $\Delta$depth')
        mpl.xlabel('$\Delta$depth (m)')
        mpl.ylabel('Air depth (m)')
        if pccfg.SHOW_INITIAL:
            mpl.plot(self.delta_depth_init, self.depth, color=pccfg.COLOR_INIT, label='Initial')
        if np.size(self.delta_depth_depth) > 0:
            mpl.errorbar(self.delta_depth_delta_depth, self.delta_depth_depth,
                         color=pccfg.COLOR_OBS,
                         xerr=self.delta_depth_sigma, linestyle='', marker='o', markersize=2,
                         label="observations")
        mpl.plot(self.delta_depth_model, self.depth, color=pccfg.COLOR_MOD, label='Prior')
        mpl.plot(self.delta_depth, self.depth, color=pccfg.COLOR_OPT, label='Posterior +/-$\sigma$')
        mpl.fill_betweenx(self.depth, self.delta_depth-self.sigma_delta_depth,
                          self.delta_depth+self.sigma_delta_depth, color=pccfg.COLOR_CI)
        x_low, x_up, y_low, y_up = mpl.axis()
        mpl.axis((x_low, x_up, self.depth[-1], self.depth[0]))
        mpl.legend(loc="best")
        printed_page = PdfPages(pccfg.DATADIR+self.label+'/Ddepth.pdf')
        printed_page.savefig(mpl.figure(self.label+' delta_depth'))
        printed_page.close()
        if not pccfg.SHOW_FIGURES:
            mpl.close()


    def save(self):
        """Save various variables for a site."""
        output = np.vstack((self.depth, self.age, self.sigma_age, self.airage, self.sigma_airage,
                            np.append(self.accu, self.accu[-1]),
                            np.append(self.sigma_accu, self.sigma_accu[-1]),
                            np.append(self.tau, self.tau[-1]),
                            np.append(self.sigma_tau, self.sigma_tau[-1]), self.lid, self.sigma_lid,
                            self.delta_depth, self.sigma_delta_depth,
                            np.append(self.a_model, self.a_model[-1]),
                            np.append(self.sigma_accu_model, self.sigma_accu_model[-1]),
                            np.append(self.tau_model, self.tau_model[-1]),
                            np.append(self.sigma_tau_model, self.sigma_tau_model[-1]),
                            self.lid_model, self.sigma_lid_model,
                            np.append(self.icelayerthick, self.icelayerthick[-1]),
                            np.append(self.sigma_icelayerthick, self.sigma_icelayerthick[-1]),
                            np.append(self.airlayerthick, self.airlayerthick[-1]),
                            np.append(self.sigma_airlayerthick, self.sigma_airlayerthick[-1])))
        with open(pccfg.DATADIR+self.label+'/output.txt', 'w') as file_save:
            file_save.write('#depth\tage\tsigma_age\tair_age\tsigma_air_age\taccu\tsigma_accu\
                    \tthinning\
                    \tsigma_thinning\tLID\tsigma_LID\tdelta_depth\tsigma_delta_depth\taccu_model\
                    \tsigma_accu_model\tthinning_model\tsigma_thinning_model\tLID_model\
                    \tsigma_LID_model\ticelayerthick\tsigma_icelayerthick\tairlayerthick\
                    \tsigma_airlayerthick\n')
            np.savetxt(file_save, np.transpose(output), delimiter='\t')
        np.savetxt(pccfg.DATADIR+self.label+'/restart.txt', np.transpose(self.variables))

#    def udepth_save(self):
#        np.savetxt(pccfg.DATADIR+self.label+'/udepth.txt',self.udepth)