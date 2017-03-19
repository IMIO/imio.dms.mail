# -*- coding: utf-8 -*-
from Products.CMFPlone.utils import _createObjectByType
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from plone.testing import z2
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing.helpers import PloneWithPackageLayer
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting

from Testing import ZopeTestCase as ztc

import imio.dms.mail


class DmsmailLayer(PloneWithPackageLayer):

    def setUpPloneSite(self, portal):
        # we create a front-page document that will be modified in setup
        _createObjectByType('Document', portal, id='front-page')
        portal.setDefaultPage('front-page')
        manage_addExternalMethod(portal, 'import_scanned', 'import_scanned', 'imio.dms.mail.demo', 'import_scanned')
        manage_addExternalMethod(portal, 'import_scanned2', 'import_scanned2', 'imio.dms.mail.demo', 'import_scanned2')
        manage_addExternalMethod(portal, 'create_main_file', 'create_main_file', 'imio.dms.mail.demo',
                                 'create_main_file')
        manage_addExternalMethod(portal, 'lock-unlock', '', 'imio.dms.mail.robot', 'lock')
        manage_addExternalMethod(portal, 'deactivate_message', '', 'imio.dms.mail.robot', 'deactivate_message')

        # install dmsmail (apply profile)
        sp = portal.portal_properties.site_properties
        sp.default_language = 'fr'
        super(DmsmailLayer, self).setUpPloneSite(portal)

    def setUpZope(self, app, configurationContext):
        ztc.utils.setupCoreSessions(app)
        super(DmsmailLayer, self).setUpZope(app, configurationContext)

DMSMAIL_FIXTURE = DmsmailLayer(
    zcml_filename="testing.zcml",
    zcml_package=imio.dms.mail,
    additional_z2_products=(
        'Products.PythonScripts',
        'imio.dashboard',
        'imio.dms.mail',
        'Products.PasswordStrength'),
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
