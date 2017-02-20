import os
from zope.i18nmessageid import MessageFactory
from datetime import date

_ = MessageFactory("imio.dms.mail")


def initialize(context):
    """Initializer called when used as a Zope 2 product."""

from collective.dms.basecontent import dmsfile
dmsfile.DmsFile.__ac_local_roles_block__ = False
dmsfile.DmsAppendixFile.__ac_local_roles_block__ = False

EMPTY_STRING = '__empty_string__'
EMPTY_DATE = date(1950, 1, 1)

PRODUCT_DIR = os.path.dirname(__file__)


def add_path(path):
    path = path.strip('/ ')
    return "%s/%s" % (PRODUCT_DIR, path)
