from AccessControl.Permissions import delete_objects
from collective.dms.basecontent import dmsfile
from datetime import date
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

EMPTY_STRING = '__empty_string__'
EMPTY_DATE = date(1950, 1, 1)

DOC_ASSIGNED_USER_FUNCTIONS = ['editeur', 'validateur']

PRODUCT_DIR = os.path.dirname(__file__)

BACK_OR_AGAIN_ICONS = {'': False,
                       'back': '++resource++imio.dms.mail/wf_back.png',
                       'again': '++resource++imio.dms.mail/wf_again.png'}


def _tr(msgid, domain='imio.dms.mail'):
    translation_domain = queryUtility(ITranslationDomain, domain)
    sp = api.portal.get().portal_properties.site_properties
    return translation_domain.translate(msgid, target_language=sp.getProperty('default_language', 'fr'))


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
    klass.manage_delObjects__roles__ = ('Authenticated', 'Member')
