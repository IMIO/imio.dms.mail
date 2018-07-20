# -*- coding: utf-8 -*-
from collections import OrderedDict

import datetime


def change_levels(cid, childs, orgs):
    lvl = orgs[cid]['lev']+1
    for id in childs[cid]:
        orgs[id]['lev'] = lvl
        if id in childs:
            change_levels(id, childs, orgs)


def sort_by_level(orgs):
    return OrderedDict(sorted(orgs.items(), key=lambda item: (item[1]['lev'], item[1]['tit'])))


def assert_value_in_list(val, lst):
    assert val in lst, "Value '%s' not in valid values '%s'" % (val, lst)
    return val


def assert_date(val, fmt='%Y/%m/%d', can_be_empty=True):
    if not val and can_be_empty:
        return None
    try:
        dtm = datetime.datetime.strptime(val, fmt)
        dt = dtm.date()
    except Exception, ex:
        raise AssertionError(u"Not a valid date '%s': %s" % (val, ex))
    return dt
