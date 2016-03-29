# -*- coding: utf-8 -*-
from collections import OrderedDict


def change_levels(cid, childs, orgs):
    lvl = orgs[cid]['lev']+1
    for id in childs[cid]:
        orgs[id]['lev'] = lvl
        if id in childs:
            change_levels(id, childs, orgs)


def sort_by_level(orgs):
    return OrderedDict(sorted(orgs.items(), key=lambda item: (item[1]['lev'], item[1]['tit'])))
