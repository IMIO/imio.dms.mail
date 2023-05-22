from AccessControl.Permissions import delete_objects
from collective.dms.basecontent import dmsfile
from datetime import date
from Globals import DevelopmentMode
from plone import api
from plone.dexterity.content import Container
from Products.Archetypes.BaseFolder import BaseFolder
from Products.CMFPlone.PloneFolder import BasePloneFolder
from zope.component import queryUtility
from zope.i18n.interfaces import ITranslationDomain
from zope.i18nmessageid import MessageFactory

import os


_ = MessageFactory("imio.dms.mail")


def initialize(context):
    """Initializer called when used as a Zope 2 product."""


dmsfile.DmsFile.__ac_local_roles_block__ = False
dmsfile.DmsAppendixFile.__ac_local_roles_block__ = False

AUC_RECORD = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.assigned_user_check'
CREATING_GROUP_SUFFIX = u'group_encoder'
CONTACTS_PART_SUFFIX = u'contacts_part'
# CREATING_FIELD_ROLE = 'Creating Group Field Writer'
EMPTY_STRING = '__empty_string__'
EMPTY_DATE = date(1950, 1, 1)
PRODUCT_DIR = os.path.dirname(__file__)
BLDT_DIR = '/'.join(os.environ.get('INSTANCE_HOME', '').split('/')[:-2])

ALL_EDITOR_SERVICE_FUNCTIONS = ['encodeur', 'editeur', 'n_plus_1', 'n_plus_2', 'n_plus_3', 'n_plus_4', 'n_plus_5']
IM_EDITOR_SERVICE_FUNCTIONS = ['editeur', 'n_plus_1', 'n_plus_2', 'n_plus_3', 'n_plus_4', 'n_plus_5']
IM_READER_SERVICE_FUNCTIONS = ['lecteur', 'editeur', 'n_plus_1', 'n_plus_2', 'n_plus_3', 'n_plus_4', 'n_plus_5']
OM_EDITOR_SERVICE_FUNCTIONS = ['encodeur', 'n_plus_1', 'n_plus_2', 'n_plus_3', 'n_plus_4', 'n_plus_5']
OM_READER_SERVICE_FUNCTIONS = ['encodeur', 'lecteur', 'editeur', 'n_plus_1', 'n_plus_2', 'n_plus_3',
                               'n_plus_4', 'n_plus_5']
TASK_EDITOR_SERVICE_FUNCTIONS = ['editeur', 'n_plus_1']

BACK_OR_AGAIN_ICONS = {'': False,
                       'back': '++resource++imio.dms.mail/wf_back.png',
                       'again': '++resource++imio.dms.mail/wf_again.png'}
PERIODS = {'month': '%Y%m', 'week': '%Y%U', 'day': '%Y%m%d'}
MAIN_FOLDERS = {'dmsincomingmail': 'incoming-mail', 'dmsincoming_email': 'incoming-mail',
                'dmsoutgoingmail': 'outgoing-mail'}
GE_CONFIG = {  # group_encoder config
    'imail_group_encoder': {'pt': ['dmsincomingmail', 'dmsincoming_email'], 'idx': 'assigned_group'},
    'omail_group_encoder': {'pt': ['dmsoutgoingmail'], 'idx': 'assigned_group'},
    'contact_group_encoder': {'pt': ['organization', 'person', 'held_position', 'contact_list'], 'idx': None},
}


def _tr(msgid, domain='imio.dms.mail', mapping=None):
    translation_domain = queryUtility(ITranslationDomain, domain)
    sp = api.portal.get().portal_properties.site_properties
    return translation_domain.translate(msgid, target_language=sp.getProperty('default_language', 'fr'),
                                        mapping=mapping)


def add_path(path):
    path = path.strip('/ ')
    return "%s/%s" % (PRODUCT_DIR, path)


# We modify the protection ('Delete objects' permission) on container manage_delObjects method
# Normally to delete an item, user must have the delete permission on the item and on the parent container
# Now container 'manage_delObjects' method is protected by roles (Member)
# Based on what is done in AccessControl.class_init
for klass in (BaseFolder, BasePloneFolder, Container):
    new = []
    for perm in klass.__ac_permissions__:
        if perm[0] == delete_objects:
            if len(perm[1]) > 1:
                methods = list(perm[1])
                methods.remove('manage_delObjects')
                perm[1] = tuple(methods)
            else:
                continue
        new.append(perm)
    klass.__ac_permissions__ = tuple(new)
    # original value ('Manager', 'Site Administrator', 'Editor', 'Contributor', '_Delete_objects_Permission')
    klass.manage_delObjects__roles__ = ('Authenticated', 'Member')

pmh = os.environ.get('ENABLE_PRINTING_MAILHOST', None)
PMH_ENABLED = False
if (pmh is not None and pmh.lower() in ('yes', 'y', 'true', 'on')) or (pmh is None and DevelopmentMode is True):
    PMH_ENABLED = True

ARCHIVE_SITE = False
if '_archives_' in BLDT_DIR:
    ARCHIVE_SITE = True
