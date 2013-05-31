# -*- coding: utf-8 -*-
import unittest2 as unittest
from zope.component import getMultiAdapter, getUtility
from plone.app.testing import setRoles, TEST_USER_ID, TEST_USER_NAME, login, logout
#from plone.dexterity.utils import createContentInContainer
from plone.portlets.interfaces import IPortletManager, IPortletRenderer
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.dms.mail.browser import portlets


class TestPortlets(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        # you'll want to use this to set up anything you need for your tests
        # below
        self.portal = self.layer['portal']

    def test_getIncomingMailFolder(self):
        self.assertEquals(portlets.getIncomingMailFolder(), self.portal.unrestrictedTraverse('/plone/incoming-mail'))

    def test_getIncomingMailAddUrl(self):
        self.assertEquals(portlets.getIncomingMailAddUrl(), 'http://nohost/plone/incoming-mail/++add++dmsincomingmail')

    def test_renderer_methods_as_admin(self):
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        view = self.portal.restrictedTraverse('@@plone')
        manager = getUtility(IPortletManager, name='plone.leftcolumn', context=self.portal)
        renderer = getMultiAdapter((self.portal, self.portal.REQUEST, view, manager, portlets.Assignment()),
                                   IPortletRenderer)
        self.assertTrue(renderer.available)
        directory_renderer = getMultiAdapter((self.portal['contacts'], self.portal.REQUEST, view, manager,
                                             portlets.Assignment()), IPortletRenderer)
        self.assertFalse(directory_renderer.available)
        self.assertTrue(renderer.canAddIncomingMail())
        self.assertFalse(renderer.canAddMainFile())
        self.assertTrue(renderer.canAddSomething())
        mail_renderer = getMultiAdapter((self.portal['incoming-mail']['courrier1'], self.portal.REQUEST, view,
                                        manager, portlets.Assignment()), IPortletRenderer)
        self.assertTrue(mail_renderer.canAddMainFile())
        self.assertEquals(renderer.getIncomingMailAddUrl(), 'http://nohost/plone/incoming-mail/++add++dmsincomingmail')
        self.assertEquals(mail_renderer.getMainFileAddUrl(), 'http://nohost/plone/incoming-mail/courrier1/++add++dmsmainfile')

    def test_renderer_methods_as_member(self):
        setRoles(self.portal, TEST_USER_ID, ['Member'])
        view = self.portal.restrictedTraverse('@@plone')
        manager = getUtility(IPortletManager, name='plone.leftcolumn', context=self.portal)
        renderer = getMultiAdapter((self.portal, self.portal.REQUEST, view, manager, portlets.Assignment()),
                                   IPortletRenderer)
        mail_renderer = getMultiAdapter((self.portal['incoming-mail']['courrier1'], self.portal.REQUEST, view,
                                        manager, portlets.Assignment()), IPortletRenderer)
        self.assertFalse(renderer.canAddIncomingMail())
        self.assertFalse(renderer.canAddMainFile())
        self.assertFalse(mail_renderer.canAddMainFile())
        self.assertFalse(renderer.canAddSomething())
