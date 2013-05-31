# -*- coding: utf-8 -*-
try:
    from collective.dms.basecontent._field import LocalRolesToPrincipalsDataManager
except ImportError:
    from collective.z3cform.rolefield.field import LocalRolesToPrincipalsDataManager


def setLocalRolesToPrincipals(self, value):
    """
        patch for LocalRolesToPrincipals
    """
    print "in setLocalRolesToPrincipals monkey patch"
    super(LocalRolesToPrincipalsDataManager, self).set(value)
