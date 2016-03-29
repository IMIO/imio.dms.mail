# -*- coding: utf-8 -*-
from collections import OrderedDict
import unittest
from ..imports import change_levels, sort_by_level


class TestImport(unittest.TestCase):

    def test_change_levels(self):
        orgs_o = OrderedDict([(i, {'lev': 1}) for i in range(1, 9)])
        childs = {1: [2, 3], 2: [4], 4: [5], 6: [7], 7: [8]}
        orgs_r = {1: {'lev': 1}, 2: {'lev': 2}, 3: {'lev': 2}, 4: {'lev': 3}, 5: {'lev': 4}, 6: {'lev': 1},
                  7: {'lev': 2}, 8: {'lev': 3}}
        # test 1
        orgs = orgs_o.copy()
        start = [1, 2, 4, 6, 7]
        for idp in start:
            change_levels(idp, childs, orgs)
        self.assertDictEqual(orgs_r, orgs)
        # test 2
        orgs = orgs_o.copy()
        start = [7, 6, 4, 2, 1]
        for idp in start:
            change_levels(idp, childs, orgs)
        self.assertDictEqual(orgs_r, orgs)
        # test 3
        orgs = orgs_o.copy()
        start = [7, 6, 4, 1, 2]
        for idp in start:
            change_levels(idp, childs, orgs)
        self.assertDictEqual(orgs_r, orgs)

    def test_sort_by_level(self):
        orgs_o = OrderedDict([(1, {'lev': 1, 'tit': 'ab'}), (2, {'lev': 2, 'tit': 'aa'}), (3, {'lev': 2, 'tit': 'ac'}),
                              (4, {'lev': 3, 'tit': 'aa'}), (5, {'lev': 4, 'tit': 'aa'}), (6, {'lev': 1, 'tit': 'aa'}),
                              (7, {'lev': 2, 'tit': 'ab'}), (8, {'lev': 3, 'tit': 'bb'})])
        orgs_r = OrderedDict([
            (6, {'lev': 1, 'tit': 'aa'}),
            (1, {'lev': 1, 'tit': 'ab'}),
            (2, {'lev': 2, 'tit': 'aa'}),
            (7, {'lev': 2, 'tit': 'ab'}),
            (3, {'lev': 2, 'tit': 'ac'}),
            (4, {'lev': 3, 'tit': 'aa'}),
            (8, {'lev': 3, 'tit': 'bb'}),
            (5, {'lev': 4, 'tit': 'aa'}),
        ])
        orgs = sort_by_level(orgs_o)
        self.assertListEqual(orgs_r.keys(), orgs.keys())
