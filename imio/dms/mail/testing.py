# -*- coding: utf-8 -*-

from plone.testing import z2, zca
from plone.app.testing import PloneWithPackageLayer
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting
import imio.dms.mail

DMSMAIL_ZCML = zca.ZCMLSandbox(filename="testing.zcml",
                             package=imio.dms.mail,
                             name='DMSMAIL_ZCML')

DMSMAIL_Z2 = z2.IntegrationTesting(bases=(z2.STARTUP, DMSMAIL_ZCML),
                                 name='DMSMAIL_Z2')

DMSMAIL_FIXTURE = PloneWithPackageLayer(
    zcml_filename="testing.zcml",
    zcml_package=imio.dms.mail,
    additional_z2_products=('Products.PythonScripts', 'imio.dms.mail',),
    gs_profile_id='imio.dms.mail:testing',
    name="DMSMAIL_FIXTURE")

DMSMAIL_INTEGRATION_TESTING = \
    IntegrationTesting(bases=(DMSMAIL_FIXTURE, ),
                       name="DmsMailFixture:Integration")

DMSMAIL_FUNCTIONAL_TESTING = \
    FunctionalTesting(bases=(DMSMAIL_FIXTURE, ),
                       name="DmsMailFixture:Functional")
