import unittest

import pandas as pd
from numpy import NaN
from pgmpy.estimators import MaximumLikelihoodEstimator
from pgmpy.estimators import BaseEstimator
from pgmpy.factors import TabularCPD


class TestBaseEstimator(unittest.TestCase):
    def setUp(self):
        self.d1 = pd.DataFrame(data={'A': [0, 0, 1], 'B': [0, 1, 0], 'C': [1, 1, 0], 'D': ['X', 'Y', 'Z']})
        self.d2 = pd.DataFrame(data={'A': [0, NaN, 1], 'B': [0, 1, 0], 'C': [1, 1, NaN], 'D': [NaN, 'Y', NaN]})

    def test_state_count(self):
        e = BaseEstimator(self.d1)
        self.assertEqual(e.state_counts('A').values.tolist(), [[2], [1]])
        self.assertEqual(e.state_counts('C', ['A', 'B']).values.tolist(),
                         [[0., 0., 1., 0.], [1., 1., 0., 0.]])

    def test_missing_data(self):
        e = BaseEstimator(self.d2, state_names={'C': [0, 1]}, complete_samples_only=False)
        self.assertEqual(e.state_counts('A', complete_samples_only=True).values.tolist(), [[0], [0]])
        self.assertEqual(e.state_counts('A').values.tolist(), [[1], [1]])
        self.assertEqual(e.state_counts('C', parents=['A', 'B'], complete_samples_only=True).values.tolist(),
                         [[0, 0, 0, 0], [0, 0, 0, 0]])
        self.assertEqual(e.state_counts('C', parents=['A', 'B']).values.tolist(),
                         [[0, 0, 0, 0], [1, 0, 0, 0]])

    def tearDown(self):
        del self.d1
