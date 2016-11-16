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

from cgpm.crosscat.engine import Engine
from cgpm.utils import general as gu
from cgpm.utils import test as tu


def retrieve_normal_dataset():
    D, Zv, Zc = tu.gen_data_table(
        n_rows=20,
        view_weights=None,
        cluster_weights=[[.2,.2,.2,.4],],
        cctypes=['normal'],
        distargs=[None],
        separation=[0.95],
        view_partition=[0],
        rng=gu.gen_rng(12))
    return D


def test_simple_diagnostics():
    D = retrieve_normal_dataset()
    engine = Engine(D.T, cctypes=['normal']*len(D), rng=gu.gen_rng(12))
    engine.transition(N=20, checkpoint=2, multiprocess=True)
    assert all(
        all(len(v) == 10 for v in state.diagnostics.itervalues())
        for state in engine.states
    )
    engine.transition(N=7, checkpoint=2, multiprocess=True)
    assert all(
        all(len(v) == 13 for v in state.diagnostics.itervalues())
        for state in engine.states
    )
    engine.transition(S=0.5, multiprocess=True)
    assert all(
        all(len(v) == 13 for v in state.diagnostics.itervalues())
        for state in engine.states
    )
    engine.transition(S=0.5, checkpoint=1, multiprocess=True)
    assert all(
        all(len(v) > 13 for v in state.diagnostics.itervalues())
        for state in engine.states
    )
