# -*- coding: utf-8 -*-

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import numpy as np
import math
import gpmcc.utils.general as gu

from scipy.stats import norm

from gpmcc import dim

from gpmcc.cc_types import normal_uc
from gpmcc.cc_types import beta_uc
from gpmcc.cc_types import normal
from gpmcc.cc_types import binomial
from gpmcc.cc_types import multinomial
from gpmcc.cc_types import lognormal
from gpmcc.cc_types import poisson
from gpmcc.cc_types import vonmises
from gpmcc.cc_types import vonmises_uc

_is_uncollapsed = {
    'normal'      : False,
    'normal_uc'   : True,
    'beta_uc'   : True,
    'binomial'    : False,
    'multinomial' : False,
    'lognormal'   : False,
    'poisson'     : False,
    'vonmises'    : False,
    'vonmises_uc' : True,
    }

_cctype_class = {
    'normal'      : normal.Normal,
    'normal_uc'   : normal_uc.NormalUC,
    'beta_uc'     : beta_uc.BetaUC,
    'binomial'    : binomial.Binomial,
    'multinomial' : multinomial.Multinomial,
    'lognormal'   : lognormal.Lognormal,
    'poisson'     : poisson.Poisson,
    'vonmises'    : vonmises.Vonmises,
    'vonmises_uc' : vonmises_uc.VonmisesUC,
    }

def gen_data_table(n_rows, view_weights, cluster_weights, cc_types, distargs,
        separation, return_dims=False):
    """Generates data, partitions, and Dim.

     input arguments:
     -- n_rows: number of rows (data points)
     -- view_weights: A n_views length np array of floats that sum to one.
     Weights for generating views.
     -- cluster_weights: A n_views length list of n_cluster length np arrays
     that sum to one. Weights for row tp cluster assignments.
     -- cc_types: n_columns length list os string specifying the data types for
     each column
     -- distargs: a list of distargs for each column (see documentation for
     each data type for info on distargs)
     -- separation: a n_cols length list of cluster separation values [0,1].
     Larger C implies more separation

     optional_arguments:
     -- return_dims: return the cc_dim objects for each column

     Returns:
     -- T : np.ndarray(n_cols, n_rows), each row in T is a column of data,
     (tranpose of a design matrix).

     example:
     >>> n_rows = 500
     >>> view_weights = np.ones(1)
     >>> cluster_weights = [np.ones(2)/2.0]
     >>> cc_types = ['lognormal','normal','poisson','multinomial','vonmises','binomial']
     >>> distargs = [None, None, None, {'K':5}, None, None]
     >>> separation = [.9]*6
     >>> T, Zv, Zc, dims = tu.gen_data_table( n_rows, view_weights,
             cluster_weights, cc_types, distargs, separation, return_dims=True)
    """
    n_cols = len(cc_types)
    Zv, Zc = gen_partition_from_weights(n_rows, n_cols, view_weights,
        cluster_weights)
    T = np.zeros((n_cols, n_rows))

    for col in range(n_cols):
        cc_type = cc_types[col]
        args = distargs[col]
        view = Zv[col]
        Tc = _gen_data[cc_type](Zc[view], separation[col], distargs=args)
        T[col] = Tc

    if return_dims:
        dims = gen_dims_from_structure(T, Zv, Zc, cc_types, distargs)
        return T, Zv, Zc, dims
    else:
        return T, Zv, Zc

def gen_dims_from_structure(T, Zv, Zc, cc_types, distargs):
    n_cols = len(Zv)
    dims = []
    for c in range(n_cols):
        v = Zv[c]
        cc_type = cc_types[c]
        cc_type_class = _cctype_class[cc_type]
        mode = 'collapsed'
        if _is_uncollapsed[cc_type]:
            mode = 'uncollapsed'
        dim_c = dim.Dim(T[c], cc_type_class, c, Zr=Zc[v], mode=mode,
                distargs=distargs[c])
        dims.append(dim_c)

    return dims

def _gen_beta_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    K = np.max(Z)+1
    alphas = np.linspace(.5 -.5*separation*.85, .5 + .5*separation*.85, K)
    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        alpha = alphas[cluster]
        beta = (1.0-alpha)*20.0*(norm.pdf(alpha,.5,.25))
        alpha *= 20.0*norm.pdf(alpha,.5,.25)
        # beta *= 10.0
        Tc[r] = np.random.beta(alpha, beta)

    return Tc

def _gen_normal_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        mu = cluster*(5.0*separation)
        sigma = 1.0
        Tc[r] = np.random.normal(loc=mu, scale=sigma)

    return Tc

def _gen_vonmises_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    num_clusters =  max(Z)+1
    sep = (2*math.pi/num_clusters)

    mus = [c*sep for c in range(num_clusters)]
    std = sep/(5.0*separation**.75)
    k = 1/(std*std)

    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        mu = mus[cluster]
        Tc[r] = np.random.vonmises(mu, k) + math.pi

    return Tc

def _gen_poisson_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    Tc = np.zeros(n_rows)

    for r in range(n_rows):
        cluster = Z[r]
        lam = (cluster)*(4.0*separation)+1
        Tc[r] = np.random.poisson(lam)

    return Tc

def _gen_lognormal_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    if separation > .9:
        separation = .9

    Tc = np.zeros(n_rows)
    for r in range(n_rows):
        cluster = Z[r]
        mu = cluster*(.9*separation**2)
        Tc[r] = np.random.lognormal(mean=mu,
            sigma=(1.0-separation)/(cluster+1.0))

    return Tc

def _gen_binomial_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)

    Tc = np.zeros(n_rows)
    K = max(Z)+1
    thetas = np.linspace(0.0,separation,K)
    for r in range(n_rows):
        cluster = Z[r]
        theta = thetas[cluster]
        x = 0.0
        if np.random.random() < theta:
            x = 1.0
        Tc[r] = x

    return Tc

def _gen_multinomial_data_column(Z, separation=.9, distargs=None):
    n_rows = len(Z)
    K = distargs['K']
    if separation > .95:
        separation = .95
    Tc = np.zeros(n_rows, dtype=int)
    C = max(Z)+1
    theta_arrays = [np.random.dirichlet(np.ones(K)*(1.0-separation), 1)
        for _ in range(C)]
    for r in range(n_rows):
        cluster = Z[r]
        thetas = theta_arrays[cluster][0]
        x = int(gu.pflip(thetas))
        Tc[r] = x
    return Tc

def gen_partition_from_weights(n_rows, n_cols, view_weights, clusters_weights):
    n_views = len(view_weights)
    Zv = [v for v in range(n_views)]
    for _ in xrange(n_cols - n_views):
        v = gu.pflip(view_weights)
        Zv.append(v)

    np.random.shuffle(Zv)
    assert len(Zv) == n_cols

    Zc = []
    for v in xrange(n_views):
        n_clusters = len(clusters_weights[v])
        Z = [c for c in range(n_clusters)]
        for _ in range(n_rows-n_clusters):
            c_weights = np.copy(clusters_weights[v])
            c = gu.pflip(c_weights)
            Z.append(c)
        np.random.shuffle(Z)
        Zc.append(Z)

    assert len(Zc) == n_views
    assert len(Zc[0]) == n_rows

    return Zv, Zc

def gen_partition_crp(n_rows, n_cols, n_views, alphas):
    Zv = [v for v in range(n_views)]
    for _ in range(n_cols-n_views):
        Zv.append(np.random.randrange(n_views))
    np.random.shuffle(Zv)
    Zc = []
    for v in range(n_views):
        Zc.append(gu.crp_gen(n_rows, alphas[v])[0])

    return Zv, Zc

def column_average_ari(Zv, Zc, cc_state_object):
    from sklearn.metrics import adjusted_rand_score
    ari = 0
    n_cols = len(Zv)
    for col in range(n_cols):
        view_t = Zv[col]
        Zc_true = Zc[view_t]

        view_i = cc_state_object.Zv[col]
        Zc_inferred = cc_state_object.views[view_i].Z.tolist()
        ari += adjusted_rand_score(Zc_true, Zc_inferred)

    return ari/float(n_cols)

def gen_sine_wave(N, noise=.5):
    x_range = [-3.0*math.pi/2.0, 3.0*math.pi/2.0]
    X = np.zeros( (N,2) )
    for i in range(N):
        x = np.random.uniform(x_range[0], x_range[1])
        y = math.cos(x)+np.random.random()*(-np.random.uniform(-noise, noise))
        X[i,0] = x
        X[i,1] = y

    T = [X[:,0],X[:,1]]
    return T

def gen_x(N, rho=.95):
    X = np.zeros( (N,2) )
    for i in range(N):
        if np.random.random() < .5:
            sigma = np.array([[1,rho],[rho,1]])
        else:
            sigma = np.array([[1,-rho],[-rho,1]])
        x = np.random.multivariate_normal(np.zeros(2), sigma)
        X[i,:] = x

    T = [X[:,0],X[:,1]]
    return T

def gen_ring(N, width=.2):
    X = np.zeros((N,2))
    for i in range(N):
        angle = np.random.uniform(0.0, 2.0*math.pi)
        distance = np.random.uniform(1.0-width, 1.0)
        X[i,0] = math.cos(angle)*distance
        X[i,1] = math.sin(angle)*distance

    T = [X[:,0],X[:,1]]
    return T

def gen_four_dots(N=200, stddev=.25):
    X = np.zeros((N,2))
    mx = [ -1, 1, -1, 1]
    my = [ -1, -1, 1, 1]
    for i in range(N):
        n = np.random.randint(4)
        x = np.random.normal(loc=mx[n], scale=stddev)
        y = np.random.normal(loc=my[n], scale=stddev)
        X[i,0] = x
        X[i,1] = y

    T = [X[:,0],X[:,1]]
    return T

_gen_data = {
    'normal_uc'  : _gen_normal_data_column,
    'beta_uc'    : _gen_beta_data_column,
    'normal'     : _gen_normal_data_column,
    'binomial'   : _gen_binomial_data_column,
    'multinomial': _gen_multinomial_data_column,
    'poisson'    : _gen_poisson_data_column,
    'lognormal'  : _gen_lognormal_data_column,
    'vonmises'   : _gen_vonmises_data_column,
    'vonmises_uc': _gen_vonmises_data_column,
}

_gen_data_cpp = {
    'continuous' : _gen_normal_data_column,
    'multinomial': _gen_multinomial_data_column,
    'magnitude'  : _gen_lognormal_data_column,
}
