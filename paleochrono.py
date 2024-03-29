"""
TODO: what about symbolic links in github?
TODO: extend the chronology down to the bedrock by extrapolating the accumulation
TODO: optinally use a restart file to have a bootstrap method
TODO: is there an elegant way to unpack the variables vector in the model function?
TODO: allow to save the correction vector to be able to restart while changing the resolution
TODO: include some checks for when ddelta_depth/dz>1
TODO: Delta-depth observations should be lognormal?
TODO: we should superpose two charts for ice and air ages, one for the age and
    one for the uncertainty, since the min age is not always near 0.
TODO: also compute the prior uncertainties and show them in the figures.
TODO: is there really a computation gain with the change of variable for the
    correction functions? Avoiding this change of variables would make the code
    easier to understand. I think there is no gain since solving A^-1 b when we
    have the LU factorisation of A does not cost more than computing A^-1 * b
    when we have computed A^-1.
"""


import sys
import time
import multiprocessing
import math as m
import numpy as np
import matplotlib.pyplot as mpl
from scipy.optimize import least_squares
import pccfg
from pcsite import Site
from pcsitepair import SitePair
from functools import partial
import gc

###Registration of start time
START_TIME = time.perf_counter()

#Read parameter file
pccfg.read_parameters()

###Opening of output.txt file
OUTPUT_FILE = open(pccfg.datadir+'output.txt', 'a')

##Global
VARIABLES = np.array([])
D = {}
DC = {}



def residuals(var):
    """Calculate the residuals as a function of the variables vector."""
    index = 0
    for i, dlab in enumerate(pccfg.list_sites):
        D[dlab].variables = var[index:index+np.size(D[dlab].variables)]
        index = index+np.size(D[dlab].variables)
        D[dlab].model(D[dlab].variables)
#    pccfg.nb_runs = pccfg.nb_runs + 1
#    gc.collect() 
    return resid()

def resid():
    """Calculate the residuals without recalculating the model."""
    resi = np.array([])
    for i, dlab in enumerate(pccfg.list_sites):
        resi = np.concatenate((resi, D[dlab].variables))
        resi = np.concatenate((resi, D[dlab].residuals()))
        for j, dlab2 in enumerate(pccfg.list_sites):
#Note that if I put a new i loop here, to separate the D and DC terms, the model runs slower
            if j < i:
                resi = np.concatenate((resi, DC[dlab2+'-'+dlab].residuals()))
    return resi
    

def cost_function(var):
    """Calculate the cost function terms related to a pair of sites."""
    res = residuals(var)
    cost = np.dot(res, np.transpose(res))
    return cost    

def jacob_column(resizero, dlabj, l):
    delta = m.sqrt(np.finfo(float).eps) #Stolen from the leastsq code
    D[dlabj].variables[l] += delta
    D[dlabj].model(D[dlabj].variables)
    deriv = [np.array([])]
    index = 0
    for i, dlab in enumerate(pccfg.list_sites):
        index = index+len(D[dlab].variables)
        if dlabj == dlab:
            der = np.zeros(len(D[dlab].variables))
            der[l] = 1.
            deriv.append(der)
            der = (D[dlab].residuals() - resizero[index:index+RESI_SIZE[i, i]]) / delta
            deriv.append(der)
        else:
            deriv.append(np.zeros(len(D[dlab].variables)))
            deriv.append(np.zeros(RESI_SIZE[i, i]))
        index = index+RESI_SIZE[i, i]
        for j, dlab2 in enumerate(pccfg.list_sites):
            if j < i:
                if dlabj == dlab or dlabj == dlab2:
                    der = (DC[dlab2+'-'+dlab].residuals()-\
                           resizero[index:index+RESI_SIZE[j, i]])/delta
                    deriv.append(der)
                else:
                    deriv.append(np.zeros(RESI_SIZE[j, i]))
                index = index+RESI_SIZE[j, i]
    D[dlabj].variables[l] -= delta
    return np.concatenate(deriv)

def jacobian_analytical(var):
    """Calculate the Jacobian of each residual term with analytical formulas."""
    jac_list = []
    for k, dlabj in enumerate(pccfg.list_sites):
        D[dlabj].corrected_jacobian()
        deriv = []
        for i, dlab in enumerate(pccfg.list_sites):
            if dlabj == dlab:
                deriv.append(np.diag(np.ones(len(D[dlab].variables))))
                deriv.append(D[dlab].residuals_jacobian())
            else:
                deriv.append(np.zeros((len(D[dlabj].variables), len(D[dlab].variables))))
                deriv.append(np.zeros((len(D[dlabj].variables), RESI_SIZE[i, i])))
            for j, dlab2 in enumerate(pccfg.list_sites):
                if j < i:
                    if dlabj == dlab:
                        deriv.append(DC[dlab2+'-'+dlab].residuals_jacobian2())
                    elif dlabj == dlab2:
                        deriv.append(DC[dlab2+'-'+dlab].residuals_jacobian1())
                    else:
                        deriv.append(np.zeros((len(D[dlabj].variables), RESI_SIZE[j, i])))
        jac_list.append(np.concatenate(deriv, axis=1))
    jacob = np.concatenate(jac_list)
#    print(np.shape(jacob), np.shape(resid()), len(VARIABLES))
    return np.transpose(jacob)

def jacobian_semi_analytical(var):
    """Calculate the Jacobian of each residual term with a finite difference scheme."""
    resizero = residuals(var)
    jac_list = []
    for k, dlabj in enumerate(pccfg.list_sites):
        if pccfg.is_parallel:
            list_args = list(range(len(D[dlabj].variables)))
            if __name__ == "__main__":
                with multiprocessing.Pool(pccfg.nb_nodes) as pool:
                    results = pool.map(partial(jacob_column, resizero, dlabj),
                                               list_args)
                jac_list.append(results)
        else:
            for l in range(len(D[dlabj].variables)):
#                jacob = np.vstack((jacob, jacob_column(resizero, dlabj, l)))
                jac_list.append(np.array([jacob_column(resizero, dlabj, l)]))
        D[dlabj].model(D[dlabj].variables)
    jacob = np.concatenate(jac_list)
    return np.transpose(jacob)

def jacobian_numerical(var):
    """Calculate the Jacobian with a finite difference scheme."""
    zeropred = residuals(var)
    derivparams = []
    results = []
    delta = m.sqrt(np.finfo(float).eps) #Stolen from the leastsq code
    #fixme: This loop is probably sub-optimal. Have a look at what does leastsq to improve this.
#        results.append(residuals(derivparams))
    if pccfg.is_parallel:
        for i in range(len(var)):
            copy = np.array(var)
            copy[i] += delta
            derivparams.append(copy)
        if __name__ == "__main__":
            pool = multiprocessing.Pool(pccfg.nb_nodes)
        results = pool.map(residuals, derivparams)
        derivs = [(r - zeropred)/delta for r in results]
    else:
        list_derivs = []
        for i in range(len(var)):
            copy = np.array(var)
            copy[i] += delta
            list_derivs.append(np.array([(residuals(copy)-zeropred)/delta]))
        derivs = np.concatenate(list_derivs)
    return np.transpose(derivs)

##MAIN

##Initialisation
RESI_SIZE = np.empty((np.size(pccfg.list_sites), np.size(pccfg.list_sites)), dtype=np.int)

for di, dlabel in enumerate(pccfg.list_sites):

    print('Initialization of site '+dlabel)

    D[dlabel] = Site(dlabel)
    D[dlabel].model(D[dlabel].variables)
#    D[dlabel].a_init=D[dlabel].a
#    D[dlabel].lid_init=D[dlabel].lid
    D[dlabel].write_init()
#    D[dlabel].display_init()
    VARIABLES = np.concatenate((VARIABLES, D[dlabel].variables))
    RESI_SIZE[di, di] = np.size(D[dlabel].residuals())

for di, dlabel in enumerate(pccfg.list_sites):
    for dj, dlabel2 in enumerate(pccfg.list_sites):
        if dj < di:
            print('Initialization of site pair '+dlabel2+'-'+dlabel)
            DC[dlabel2+'-'+dlabel] = SitePair(D[dlabel2], D[dlabel])
#            DC[dlabel2+'-'+dlabel].display_init()
            RESI_SIZE[dj, di] = np.size(DC[dlabel2+'-'+dlabel].residuals())

print('Size of VARIABLES vector', len(VARIABLES))
print('Size of RESIDUALS vector', len(resid()))

##Optimization
START_TIME_OPT = time.perf_counter()
print('cost function: ', cost_function(VARIABLES))
#print(jacobian_semi_analytical(VARIABLES))
#print(jacobian_analytical(VARIABLES))
if pccfg.opt_method == 'leastsq':
    pccfg.opt_method = 'trf'
    pccfg.is_parallel = False
elif pccfg.opt_method == 'leastsq-parallel':
    pccfg.opt_method = 'trf'
    pccfg.is_parallel = True
if pccfg.opt_method == "trf" or pccfg.opt_method == 'lm':
    print('Optimization by:', pccfg.opt_method)
    if pccfg.opt_method == 'trf':
        print('tr_solver:', pccfg.tr_solver)
    print('Jabobian:', pccfg.jacobian)
    OptimizeResult = least_squares(residuals, VARIABLES, method=pccfg.opt_method,
                                   jac=eval('jacobian_'+pccfg.jacobian),
                                   tr_solver=pccfg.tr_solver,
                                   xtol=pccfg.tol, ftol=pccfg.tol, gtol=pccfg.tol, verbose=2)
    print('Optimization execution time: ', time.perf_counter() - START_TIME_OPT, 'seconds')
    VARIABLES = OptimizeResult.x
    HESS = np.dot(np.transpose(OptimizeResult.jac), OptimizeResult.jac)
    COV = np.linalg.inv(HESS)
elif pccfg.opt_method == 'none':
    print('No optimization')
    VARIABLES = np.zeros(np.size(VARIABLES))
    COV = np.diag(np.ones(np.size(VARIABLES)))
else:
    print(pccfg.opt_method, ': Optimization method not recognized.')
    sys.exit()
#print 'solution: ',VARIABLES
print('cost function: ', cost_function(VARIABLES))
if pccfg.opt_method == 'leastsq' and np.size(COV) == 1 and COV is None:
    print('singular matrix encountered (flat curvature in some direction)')
    sys.exit()
#print('nb of model runs', pccfg.nb_runs)

print('Calculation of confidence intervals')
INDEXSITE = 0
for dlabel in pccfg.list_sites:
    D[dlabel].variables = VARIABLES[INDEXSITE:INDEXSITE+np.size(D[dlabel].variables)]
    D[dlabel].cov = COV[INDEXSITE:INDEXSITE+np.size(D[dlabel].variables),\
        INDEXSITE:INDEXSITE+np.size(D[dlabel].variables)]
    INDEXSITE = INDEXSITE+np.size(D[dlabel].variables)
    D[dlabel].sigma()

###Final display and output
print('Display and saving of results')
for di, dlabel in enumerate(pccfg.list_sites):
#    print dlabel+'\n'
    D[dlabel].save()
    D[dlabel].figures()
    for dj, dlabel2 in enumerate(pccfg.list_sites):
        if dj < di:
#            print dlabel2+'-'+dlabel+'\n'
            DC[dlabel2+'-'+dlabel].figures()

###Program execution time
MESSAGE = 'Program execution time: '+str(time.perf_counter()-START_TIME)+' seconds.'
print(MESSAGE)
OUTPUT_FILE.write(MESSAGE)

if pccfg.show_figures:
    mpl.show()

###Closing output file
OUTPUT_FILE.close()
