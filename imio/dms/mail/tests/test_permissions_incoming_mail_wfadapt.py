# -*- coding: utf-8 -*-
""" user permissions tests for this package."""
from datetime import datetime
from imio.dms.mail.testing import change_user
from imio.dms.mail.tests.test_permissions_base import TestPermissionsBase
from imio.dms.mail.utils import clean_borg_cache
from imio.dms.mail.utils import sub_create
from plone import api
from z3c.relationfield.relation import RelationValue
from zope.component import getUtility
from zope.intid.interfaces import IIntIds


class TestPermissionsIncomingMailWfAdapt(TestPermissionsBase):
    def test_permissions_incoming_mail_wfadapt(self):
        intids = getUtility(IIntIds)
        params = {
            "title": "Courrier 10",
            "mail_type": "courrier",
            "internal_reference_no": "E0010",
            "sender": [RelationValue(intids.getId(self.portal["contacts"]["jeancourant"]))],
            "treating_groups": self.portal["contacts"]["plonegroup-organization"]["direction-generale"]["grh"].UID(),
        }
        change_user(self.portal, "encodeur")
        imail = sub_create(self.imf, "dmsincomingmail", datetime.today(), "my-id", **params)
        annex = api.content.create(container=imail, id="annex", type="dmsappendixfile")
        file = api.content.create(container=imail, id="file", type="dmsmainfile")
        task = api.content.create(container=imail, id="task", type="task", assigned_group=imail.treating_groups)
        clean_borg_cache(self.portal.REQUEST)
