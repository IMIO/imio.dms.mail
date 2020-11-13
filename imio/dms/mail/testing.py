# -*- coding: utf-8 -*-
from collections import OrderedDict

from imio.dms.mail.utils import set_dms_config
from imio.pyutils.system import runCommand
from plone import api
from plone.app.robotframework.testing import REMOTE_LIBRARY_BUNDLE_FIXTURE
from plone.app.testing import FunctionalTesting
from plone.app.testing import IntegrationTesting
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing.helpers import PloneWithPackageLayer
from plone.testing import z2
from Products.CMFPlone.utils import _createObjectByType
from Products.CMFPlone.utils import base_hasattr
from Products.ExternalMethod.ExternalMethod import manage_addExternalMethod
from Testing import ZopeTestCase as ztc
from zope.globalrequest.local import setLocal
from zope.i18n import translate

import imio.dms.mail
import os


class DmsmailLayer(PloneWithPackageLayer):

    def setUpPloneSite(self, portal):
        setLocal('request', portal.REQUEST)
        manage_addExternalMethod(portal, 'import_scanned', 'import_scanned', 'imio.dms.mail.demo', 'import_scanned')
        manage_addExternalMethod(portal, 'import_scanned2', 'import_scanned2', 'imio.dms.mail.demo', 'import_scanned2')
        manage_addExternalMethod(portal, 'create_main_file', 'create_main_file', 'imio.dms.mail.demo',
                                 'create_main_file')
        manage_addExternalMethod(portal, 'activate_group_encoder', 'activate_group_encoder', 'imio.dms.mail.demo',
                                 'activate_group_encoder')
        manage_addExternalMethod(portal, 'lock-unlock', '', 'imio.dms.mail.robot', 'lock')
        manage_addExternalMethod(portal, 'robot_init', '', 'imio.dms.mail.robot', 'robot_init')

        sp = portal.portal_properties.site_properties
        sp.default_language = 'fr'
        # we create a front-page document that will be modified in setup
        _createObjectByType('Document', portal, id='front-page')
        portal.setDefaultPage('front-page')
        _createObjectByType('Folder', portal, id='Members', title='Users', description="Site Users")
        members = getattr(portal, 'Members')
        members.setTitle(translate(u'members-title', target_language='fr', domain='plonefrontpage', default='Users'))
        members.setDescription(translate(u'members-description', target_language='fr', domain='plonefrontpage',
                                         default="Site Users"))
        members.unmarkCreationFlag()
        members.setLanguage('fr')
        members.reindexObject()

        # install dmsmail (apply profile)
        super(DmsmailLayer, self).setUpPloneSite(portal)
        api.content.transition(obj=members, transition='show_internally')

        # copy template
        setRoles(portal, TEST_USER_ID, ['Manager'])
        folder_uid = portal['contacts']['plonegroup-organization']['direction-generale']['secretariat'].UID()
        newobj = api.content.copy(portal['templates']['om']['main'], portal['templates']['om'][folder_uid])
        newobj.title = u'Modèle type'
        newobj.reindexObject()

        # avoid redirection after document generation
        from imio.dms.mail.browser.documentgenerator import OMPDGenerationView
        OMPDGenerationView.redirects = lambda a, b: None

        setRoles(portal, TEST_USER_ID, ['Member'])

    def setUpZope(self, app, configurationContext):
        ztc.utils.setupCoreSessions(app)
        super(DmsmailLayer, self).setUpZope(app, configurationContext)
        from App.config import _config
        if not base_hasattr(_config, 'product_config'):
            _config.product_config = {'imio.zamqp.core': {'ws_url': 'http://localhost:6543', 'ws_password': 'test',
                                                          'ws_login': 'testuser', 'routing_key': '019999',
                                                          'client_id': '019999'}}
        (stdout, stderr, st) = runCommand('%s/bin/soffice.sh restart' % os.getenv('PWD'))

    def tearDownZope(self, app):
        """Tear down Zope."""
        (stdout, stderr, st) = runCommand('%s/bin/soffice.sh stop' % os.getenv('PWD'))


class DmsmailLayerNP1(DmsmailLayer):

    def setUpPloneSite(self, portal):
        super(DmsmailLayerNP1, self).setUpPloneSite(portal)
        setRoles(portal, TEST_USER_ID, ['Manager'])
        # Change some settings
        api.portal.set_registry_record('collective.contact.core.interfaces.IContactCoreParameters.'
                                       'contact_source_metadata_content',
                                       u'{gft} # {number}, {street}, {zip_code}, {city} # {email}')
        # Activate n+1
        portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                     'imiodmsmail-im_n_plus_1_wfadaptation', run_dependencies=False)
        portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                     'imiodmsmail-om_n_plus_1_wfadaptation', run_dependencies=False)
        portal.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:singles',
                                                     'imiodmsmail-task_n_plus_1_wfadaptation', run_dependencies=False)
        # Delete om
        brains = api.content.find(portal_type='dmsoutgoingmail')
        for brain in brains:
            api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'outgoingmail_number', 1)
        # Delete im
        brains = api.content.find(portal_type=['dmsincomingmail', 'dmsincoming_email'])
        for brain in brains:
            api.content.delete(obj=brain.getObject(), check_linkintegrity=False)
        api.portal.set_registry_record('collective.dms.mailcontent.browser.settings.IDmsMailConfig.'
                                       'incomingmail_number', 1)

        setRoles(portal, TEST_USER_ID, ['Member'])


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

DMSMAIL_NP1_FIXTURE = DmsmailLayerNP1(
    zcml_filename="testing.zcml",
    zcml_package=imio.dms.mail,
    additional_z2_products=(
        'Products.PythonScripts',
        'imio.dashboard',
        'imio.dms.mail',
        'Products.PasswordStrength'),
    gs_profile_id='imio.dms.mail:testing',
    name="DMSMAIL_NP1_FIXTURE")

DMSMAIL_INTEGRATION_TESTING = IntegrationTesting(
    bases=(DMSMAIL_FIXTURE, ),
    name="DmsMailFixture:Integration")

DMSMAIL_FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(DMSMAIL_FIXTURE, ),
    name="DmsMailFixture:Functional")

DMSMAIL_ROBOT_TESTING = FunctionalTesting(
    bases=(DMSMAIL_NP1_FIXTURE,
           REMOTE_LIBRARY_BUNDLE_FIXTURE,
           z2.ZSERVER_FIXTURE,),
    name="DMSMAIL_ROBOT_TESTING")


def reset_dms_config():
    set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'from'],  # i_e ok
                   [('created', 'back_to_creation'), ('proposed_to_manager', 'back_to_manager')])
    set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'],  # i_e ok
                   [('proposed_to_agent', 'propose_to_agent')])
    set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'from'], [('created', 'back_to_creation')])
    set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'], [('to_be_signed', 'propose_to_be_signed')])
    set_dms_config(['review_levels', 'dmsincomingmail'],  # i_e ok
                   OrderedDict([('dir_general', {'st': ['proposed_to_manager']})]))
    set_dms_config(['review_levels', 'task'], OrderedDict())
    set_dms_config(['review_levels', 'dmsoutgoingmail'], OrderedDict())
    set_dms_config(['review_states', 'dmsincomingmail'],  # i_e ok
                   OrderedDict([('proposed_to_manager', {'group': 'dir_general'}),]))
    set_dms_config(['review_states', 'task'], OrderedDict())
    set_dms_config(['review_states', 'dmsoutgoingmail'], OrderedDict())
    set_dms_config(['transitions_auc', 'dmsincomingmail'], OrderedDict())  # i_e ok
    set_dms_config(['transitions_levels', 'dmsincomingmail'], OrderedDict())  # i_e ok
    set_dms_config(['transitions_levels', 'dmsoutgoingmail'], OrderedDict())
    set_dms_config(['transitions_levels', 'task'], OrderedDict())
