# -*- coding: utf-8 -*-

from Products.CMFPlone.utils import _createObjectByType
from plone.testing import z2
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import PloneWithPackageLayer
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting
import imio.dms.mail


class DmsmailLayer(PloneWithPackageLayer):

    def setUpPloneSite(self, portal):
        # we create a front-page document that will be modified in setup
        _createObjectByType('Document', portal, id='front-page')
        portal.setDefaultPage('front-page')
        # install dmsmail (apply profile)
        super(DmsmailLayer, self).setUpPloneSite(portal)

DMSMAIL_FIXTURE = DmsmailLayer(
    zcml_filename="testing.zcml",
    zcml_package=imio.dms.mail,
    additional_z2_products=('Products.PythonScripts', 'imio.dms.mail', 'Products.PasswordStrength'),
    gs_profile_id='imio.dms.mail:testing',
    name="DMSMAIL_FIXTURE")

DMSMAIL_INTEGRATION_TESTING = IntegrationTesting(
    bases=(DMSMAIL_FIXTURE, ),
    name="DmsMailFixture:Integration")

DMSMAIL_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(DMSMAIL_FIXTURE, ),
    name="DmsMailFixture:Functional")

DMSMAIL_ROBOT_TESTING = FunctionalTesting(
    bases=(DMSMAIL_FIXTURE,
           REMOTE_LIBRARY_BUNDLE_FIXTURE,
           z2.ZSERVER_FIXTURE,),
    name="DMSMAIL_ROBOT_TESTING")
