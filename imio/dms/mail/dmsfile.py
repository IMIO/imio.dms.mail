# -*- coding: utf-8 -*-

from zope.component import getUtility
from zope.interface import Invalid, implements

from plone.dexterity.schema import DexteritySchemaPolicy
from plone.namedfile.field import NamedBlobFile
from plone.namedfile.utils import get_contenttype
from plone.registry.interfaces import IRegistry
from plone.supermodel import model

from collective.dms.basecontent.dmsfile import IDmsFile, DmsFile
from collective.dms.basecontent import _ as _CDB

from . import _


class RestrictedNamedBlobFile(NamedBlobFile):

    def _validate(self, value):
        super(RestrictedNamedBlobFile, self)._validate(value)
        if value is not None:
            registry = getUtility(IRegistry)
            if registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile']:
                if (self.context.portal_type == 'dmsommainfile' and
                        self.context.file.contentType != 'application/vnd.oasis.opendocument.text'):
                    # we are editing the dmsmainfile, there was previously another type, we keep it !
                    # It's necessary to permit edition of a pdf scanned file
                    return
                mimetype = get_contenttype(value)
                if mimetype != 'application/vnd.oasis.opendocument.text':
                    raise Invalid(_('You can only upload ".odt" file (Libre Office format)'))


class IImioDmsFile(IDmsFile):
    """Schema for DmsFile"""
    model.primary('file')
    file = RestrictedNamedBlobFile(
        title=_CDB(u"File"),
        required=True,
    )


class ImioDmsFile(DmsFile):
    """DmsFile"""
    implements(IImioDmsFile)
    __ac_local_roles_block__ = False

    def Title(self):
        return self.title


class ImioDmsFileSchemaPolicy(DexteritySchemaPolicy):
    """Schema Policy for DmsFile"""

    def bases(self, schemaName, tree):
        return (IImioDmsFile, )
