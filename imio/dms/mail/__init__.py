from collective.dms.basecontent import dmsfile
from datetime import date
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


def add_path(path):
    path = path.strip('/ ')
    return "%s/%s" % (PRODUCT_DIR, path)
