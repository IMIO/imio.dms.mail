# -*- coding: utf-8 -*-

from zope.component import getUtility
from zope.interface import Invalid

from plone.dexterity.schema import DexteritySchemaPolicy
from plone.namedfile.field import NamedBlobFile
from plone.namedfile.utils import get_contenttype
from plone.registry.interfaces import IRegistry
from plone.supermodel import model

from collective.dms.basecontent.dmsfile import IDmsFile
from collective.dms.basecontent import _ as _CDB

from . import _


class RestrictedNamedBlobFile(NamedBlobFile):

    def _validate(self, value):
        super(RestrictedNamedBlobFile, self)._validate(value)
        if value is not None:
            if self.context.__parent__.portal_type == 'dmsoutgoingmail':
                registry = getUtility(IRegistry)
                if registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile']:
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


class ImioDmsFileSchemaPolicy(DexteritySchemaPolicy):
    """Schema Policy for DmsFile"""

    def bases(self, schemaName, tree):
        return (IImioDmsFile, )
