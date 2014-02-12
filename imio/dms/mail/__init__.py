from zope.i18nmessageid import MessageFactory

_ = MessageFactory("imio.dms.mail")

def initialize(context):
    """Initializer called when used as a Zope 2 product."""

from collective.dms.basecontent import dmsfile
dmsfile.DmsFile.__ac_local_roles_block__ = False
