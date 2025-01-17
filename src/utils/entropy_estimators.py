# -*- coding: utf-8 -*-
# Written by Greg Ver Steeg.
# See readme.pdf for documentation
# Or go to http://www.isi.edu/~gregv/npeet.html

from __future__ import print_function
from __future__ import division
from builtins import zip
from builtins import map
from builtins import range
from past.utils import old_div
import numpy as np
import numpy.random as nr
import random
import scipy.spatial as ss

from math import log, pi
from scipy.special import digamma, gamma

# CONTINUOUS ESTIMATORS

def entropy(x, k=3, base=2):
  """The classic K-L k-nearest neighbor continuous entropy estimator.
  x should be a list of vectors, e.g. x = [[1.3], [3.7], [5.1], [2.4]]
  if x is a one-dimensional scalar and we have four samples
  """
  assert k <= len(x)-1, 'Set k smaller than num. samples - 1.'
  d = len(x[0])
  N = len(x)
  intens = 1e-10 # Small noise to break degeneracy, see doc.
  x = [list(p + intens*nr.rand(len(x[0]))) for p in x]
  tree = ss.cKDTree(x)
  nn = [tree.query(point, k+1, p=float('inf'))[0][k] for point in x]
  const = digamma(N) - digamma(k) + d*log(2)
  return old_div((const + d*np.mean(list(map(log, nn)))), log(base))

def mi(x, y, k=3, base=2):
  """Mutual information of x and y.
  x,y should be a list of vectors, e.g. x = [[1.3], [3.7], [5.1], [2.4]]
  if x is a one-dimensional scalar and we have four samples.
  """
  assert len(x)==len(y), 'Lists should have same length.'
  assert k <= len(x) - 1, 'Set k smaller than num samples - 1.'
  intens = 1e-10 # Small noise to break degeneracy, see doc.
  x = [list(p + intens*nr.rand(len(x[0]))) for p in x]
  y = [list(p + intens*nr.rand(len(y[0]))) for p in y]
  points = zip2(x,y)
  # Find nearest neighbors in joint space, p=inf means max-norm.
  tree = ss.cKDTree(points)
  dvec = [tree.query(point, k+1, p=float('inf'))[0][k] for point in points]
  a = avgdigamma(x,dvec)
  b = avgdigamma(y,dvec)
  c = digamma(k)
  d = digamma(len(x))
  return old_div((-a-b+c+d), log(base))

def cmi(x, y, z, k=3, base=2):
  """Mutual information of x and y, conditioned on z
  x,y,z should be a list of vectors, e.g. x = [[1.3], [3.7], [5.1], [2.4]]
  if x is a one-dimensional scalar and we have four samples
  """
  assert len(x)==len(y), 'Lists should have same length.'
  assert k <= len(x) - 1, 'Set k smaller than num samples - 1.'
  intens = 1e-10 # Small noise to break degeneracy, see doc.
  x = [list(p + intens*nr.rand(len(x[0]))) for p in x]
  y = [list(p + intens*nr.rand(len(y[0]))) for p in y]
  z = [list(p + intens*nr.rand(len(z[0]))) for p in z]
  points = zip2(x,y,z)
  # Find nearest neighbors in joint space, p=inf means max-norm.
  tree = ss.cKDTree(points)
  dvec = [tree.query(point, k+1, p=float('inf'))[0][k] for point in points]
  a = avgdigamma(zip2(x,z), dvec)
  b = avgdigamma(zip2(y,z), dvec)
  c = avgdigamma(z,dvec)
  d = digamma(k)
  return old_div((-a-b+c+d), log(base))

def kldiv(x, xp, k=3, base=2):
  """KL Divergence between p and q for x~p(x),xp~q(x).
  x, xp should be a list of vectors, e.g. x = [[1.3],[3.7],[5.1],[2.4]]
  if x is a one-dimensional scalar and we have four samples
  """
  assert k <= len(x) - 1, 'Set k smaller than num samples - 1.'
  assert k <= len(xp) - 1, 'Set k smaller than num samples - 1.'
  assert len(x[0]) == len(xp[0]), 'Two distributions must have same dim.'
  d = len(x[0])
  n = len(x)
  m = len(xp)
  const = log(m) - log(n-1)
  tree = ss.cKDTree(x)
  treep = ss.cKDTree(xp)
  nn = [tree.query(point, k+1, p=float('inf'))[0][k] for point in x]
  nnp = [treep.query(point, k, p=float('inf'))[0][k-1] for point in x]
  return old_div((const + d * np.mean(list(map(log, nnp))) \
    - d * np.mean(list(map(log, nn)))), log(base))

# DISCRETE ESTIMATORS
def entropyd(sx, base=2):
  """Discrete entropy estimator.
  Given a list of samples which can be any hashable object
  """
  return entropyfromprobs(hist(sx), base=base)

def midd(x, y, base=2):
  """Discrete mutual information estimator.
  Given a list of samples which can be any hashable object
  """
  return -entropyd(list(zip(x,y)), base=base) + entropyd(x, base=base) \
    + entropyd(y, base=base)

def cmidd(x, y, z, base=2):
  """Discrete mutual information estimator.
  Given a list of samples which can be any hashable object.
  """
  return entropyd(list(zip(y,z)), base=base) + entropyd(list(zip(x,z)), base=base) \
    - entropyd(list(zip(x,y,z)), base=base) - entropyd(z, base=base)

def hist(sx):
  """Histogram from list of samples."""
  d = dict()
  for s in sx:
    d[s] = d.get(s,0) + 1
  return [float(z)/len(sx) for z in list(d.values())]

def entropyfromprobs(probs, base=2):
  # Turn a normalized list of probabilities of discrete outcomes into entropy.
  return old_div(-sum(map(elog, probs)), log(base))

def elog(x):
  # For entropy, 0 log 0 = 0. but we get an error for putting log 0.
  if x <= 0. or x>=1.:
    return 0
  else:
    return x*log(x)

# MIXED ESTIMATORS
def micd(x, y, k=3, base=2, warning=True):
  """If x is continuous and y is discrete, compute mutual information."""
  overallentropy = entropy(x, k, base)

  n = len(y)
  word_dict = dict()
  for sample in y:
    word_dict[sample] = word_dict.get(sample, 0) + 1./n
  yvals = list(set(word_dict.keys()))

  mi = overallentropy
  for yval in yvals:
    xgiveny = [x[i] for i in range(n) if y[i]==yval]
    if k <= len(xgiveny) - 1:
      mi -= word_dict[yval] * entropy(xgiveny, k, base)
    else:
      if warning:
        print("Warning, after conditioning, on y=",yval," insufficient data. Assuming maximal entropy in this case.")
      mi -= word_dict[yval] * overallentropy
  return mi # Units already applied.

# UTILITY FUNCTIONS
def vectorize(scalarlist):
  """Turn a list of scalars into a list of one-d vectors."""
  return [(x,) for x in scalarlist]

def shuffle_test(measure,x,y,z=False,ns=60,ci=0.95,**kwargs):
  """Repeatedly shuffle the x-values and then estimate measure(x,y,[z]).
  Returns the mean and conf. interval ('ci=0.95' default) over 'ns' runs.
  `measure` could me mi,cmi, e.g. Keyword arguments can be passed. mi and cmi
  should have a mean near zero.
  """
  xp = x[:] # A copy that we can shuffle.
  outputs = []
  for i in range(ns):
    random.shuffle(xp)
    if z:
      outputs.append(measure(xp, y, z, **kwargs))
    else:
      outputs.append(measure(xp, y, **kwargs))
  outputs.sort()
  return outputs
  # return np.mean(outputs), (outputs[int((1.-ci)/2*ns)], \
  #   outputs[int((1.+ci)/2*ns)])

# INTERNAL FUNCTIONS

def avgdigamma(points, dvec):
  # This part finds number of neighbors in some radius in the marginal space
  # returns expectation value of <psi(nx)>.
  N = len(points)
  tree = ss.cKDTree(points)
  avg = 0.
  for i in range(N):
    dist = dvec[i]
    # Subtlety, we don't include the boundary point,
    # but we are implicitly adding 1 to kraskov def bc center point is included.
    num_points = len(tree.query_ball_point(points[i], dist-1e-15,
      p=float('inf')))
    avg += old_div(digamma(num_points), N)
  return avg

def zip2(*args):
  #zip2(x,y) takes the lists of vectors and makes it a list of vectors in a joint space
  #E.g. zip2([[1],[2],[3]],[[4],[5],[6]]) = [[1,4],[2,5],[3,6]]
  return [sum(sublist,[]) for sublist in zip(*args)]

if __name__ == "__main__":
  print("NPEET: Non-parametric entropy estimation toolbox. See readme.pdf for details on usage.")
