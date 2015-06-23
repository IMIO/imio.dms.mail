# -*- coding: utf-8 -*-

from plone.testing import z2
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import PloneWithPackageLayer
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting
import imio.dms.mail

DMSMAIL_FIXTURE = PloneWithPackageLayer(
    zcml_filename="testing.zcml",
    zcml_package=imio.dms.mail,
    additional_z2_products=('Products.PythonScripts', 'imio.dms.mail', 'Products.PasswordStrength'),
    gs_profile_id='imio.dms.mail:testing',
    name="DMSMAIL_FIXTURE")

#DMSMAIL_FIXTURE = PloneSandboxLayer(
#    name="DMSMAIL_FIXTURE")

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
