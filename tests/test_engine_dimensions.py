# -*- coding: utf-8 -*-

# Copyright (c) 2015-2016 MIT Probabilistic Computing Project

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This test suite ensures that results returned from Engine.logpdf,
Engine.logpdf_bulk, Engine.simulate, and Engine.simulate_bulk are of the
correct dimensions, based on the number of states and type of query.

Every results from these queries should be a list of length
Engine.num_states(). The elements of the returned list differ based on the
method, where we use

    - logpdf[s] = logpdf of query from state s.

    - simulate[s][i] = sample i (i=1..N) of query from state s.

    - logpdf_bulk[s][j] = logpdf of query[j] from state s.

    - simulate_bulk[s][j][i] = sample (i=1..Ns[j]) of query[j] from state s.

This test suite is slow because many simulate/logpdf queries are invoked.
"""

import numpy as np
import pytest

from cgpm.crosscat.engine import Engine
from cgpm.utils import config as cu
from cgpm.utils import general as gu
from cgpm.utils import test as tu


@pytest.fixture(scope='module')
def engine():
    # Set up the data generation
    cctypes, distargs = cu.parse_distargs([
        'normal',
        'poisson',
        'bernoulli',
        'lognormal',
        'beta',
        'vonmises'
    ])
    T, Zv, Zc = tu.gen_data_table(
        100, [1], [[.25, .25, .5]], cctypes, distargs,
        [.95]*len(cctypes), rng=gu.gen_rng(0))
    T = T.T
    # Make some nan cells for evidence.
    T[5,0] = T[5,1] = T[5,2] = T[5,3] = np.nan
    T[8,4] = np.nan
    e = Engine(
        T,
        cctypes=cctypes,
        distargs=distargs,
        num_states=6,
        rng=gu.gen_rng(0)
    )
    e.transition(N=2)
    return e.to_metadata()


def test_logpdf__ci_(engine):
    engine = Engine.from_metadata(engine)

    def test_correct_dimensions(rowid, query, evidence):
        # logpdfs should be a list of floats.
        logpdfs = engine.logpdf(rowid, query, evidence=evidence)
        assert len(logpdfs) == engine.num_states()
        for state_logpdfs in logpdfs:
            # Each element in logpdfs should be a single float.
            assert isinstance(state_logpdfs, float)
        lp = engine._likelihood_weighted_integrate(
            logpdfs, rowid, evidence=evidence)
        assert isinstance(lp, float)

    test_correct_dimensions(-1, {0:1}, {2:1, 3:.5})
    test_correct_dimensions(-1, {2:0, 5:3}, {0:4, 1:5})
    test_correct_dimensions(5, {0:0, 2:0}, {3:3})


def test_simulate__ci_(engine):
    engine = Engine.from_metadata(engine)

    def test_correct_dimensions(rowid, query, evidence, N):
        samples = engine.simulate(rowid, query, evidence=evidence, N=N)
        assert len(samples) == engine.num_states()
        for states_samples in samples:
            # Each element of samples should be a list of N samples.
            assert len(states_samples) == N
            for s in states_samples:
                # Each raw sample should be len(Q) dimensional.
                assert set(s.keys()) == set(query)
                assert len(s) == len(query)
        s = engine._likelihood_weighted_resample(
            samples, rowid, evidence=evidence)
        assert len(s) == N

    query1, evidence1 = [0], {2:0, 3:6}
    query2, evidence2 = [1,2,5], {0:3, 3:.8}

    test_correct_dimensions(-1, query1, evidence1, 1)
    test_correct_dimensions(-1, query1, evidence1, 8)
    test_correct_dimensions(-1, query2, evidence2, 1)
    test_correct_dimensions(-1, query2, evidence2, 8)

    query3, evidence3 = [0,1,2], {3:1}
    test_correct_dimensions(5, query3, evidence3, 1)
    test_correct_dimensions(5, query3, evidence3, 8)


def test_logpdf_bulk__ci_(engine):
    engine = Engine.from_metadata(engine)
    rowid1, query1, evidence1 = 5, {0:0}, {2:1, 3:.5}
    rowid2, query2, evidence2 = -1, {1:0, 4:.8}, {5:.5}
    # Bulk.
    rowids = [rowid1, rowid2]
    queries = [query1, query2]
    evidences = [evidence1, evidence2]
    # Invoke
    logpdfs = engine.logpdf_bulk(
        rowids, queries, evidences=evidences)
    assert np.allclose(len(logpdfs), engine.num_states())
    for state_logpdfs in logpdfs:
        # state_logpdfs should be a list of floats, one float per query.
        assert len(state_logpdfs) == len(rowids)
        for l in state_logpdfs:
                assert isinstance(l, float)


def test_simulate_bulk__ci_(engine):
    engine = Engine.from_metadata(engine)
    rowid1, query1, evidence1, N1, = -1, [0,2,4,5], {3:1}, 7
    rowid2, query2, evidence2, N2 = 5, [1,3], {2:1}, 3
    rowid3, query3, evidence3, N3 = 8, [0], {4:.8}, 3
    # Bulk.
    rowids = [rowid1, rowid2, rowid3]
    queries = [query1, query2, query3]
    evidences = [evidence1, evidence2, evidence3]
    Ns = [N1, N2, N3]
    # Invoke
    samples = engine.simulate_bulk(
        rowids, queries, evidences=evidences, Ns=Ns)
    assert len(samples) == engine.num_states()
    for states_samples in samples:
        assert len(states_samples) == len(rowids)
        for i, sample in enumerate(states_samples):
            assert len(sample) == Ns[i]
            for s in sample:
                assert set(s.keys()) == set(queries[i])
                assert len(s) == len(queries[i])
