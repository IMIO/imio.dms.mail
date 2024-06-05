# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.utils import get_person_from_userid
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.content.behaviors import default_creating_group
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.test_helpers import ImioTestHelpers
from plone import api
from plone.app.testing import logout
from zope.component import getUtility
from zope.intid.interfaces import IIntIds

import unittest


class TestContentBehaviors(unittest.TestCase, ImioTestHelpers):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.change_user("siteadmin")
        self.pgof = self.portal["contacts"]["plonegroup-organization"]
        self.intids = getUtility(IIntIds)

    def test_default_creating_group(self):
        self.change_user("agent")
        self.assertIsNone(default_creating_group())
        # we activate contact group encoder
        api.portal.set_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_group_encoder", True)
        orgs = get_registry_organizations()
        # selected orgs
        # u'Direction générale', (u'Secrétariat', u'GRH', u'Communication')
        # u'Direction financière', (u'Budgets', u'Comptabilité')
        # u'Direction technique', (u'Bâtiments', u'Voiries')
        # u'Événements'
        functions = get_registry_functions()
        self.assertEqual(u"group_encoder", functions[-1]["fct_id"])
        self.assertIsNone(default_creating_group())
        # we configure the function orgs
        functions[-1]["fct_orgs"] = [orgs[1], orgs[2], orgs[3]]
        set_registry_functions(functions)
        self.assertIsNone(default_creating_group())
        # we add user in groups
        for org in functions[-1]["fct_orgs"]:
            api.group.add_user(groupname="{}_{}".format(org, CREATING_GROUP_SUFFIX), username="agent")
        self.assertEqual(default_creating_group(), orgs[3])  # primary org
        # user not in selected groups: no interaction
        self.assertEqual(default_creating_group(api.user.get(userid="agent1")), orgs[1])
        # we change the primary organization
        get_person_from_userid("agent").primary_organization = None
        self.assertEqual(default_creating_group(api.user.get(userid="agent")), orgs[1])
        # user logout
        logout()
