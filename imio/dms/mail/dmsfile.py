# -*- coding: utf-8 -*-

from collective.dms.basecontent import _ as _CDB
from collective.dms.basecontent.dmsfile import DmsFile
from collective.dms.basecontent.dmsfile import IDmsFile
from imio.dms.mail import _
from imio.dms.mail.browser.settings import OMFileFormatsVocabulary
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.namedfile.field import NamedBlobFile
from plone.namedfile.utils import get_contenttype
from plone.registry.interfaces import IRegistry
from plone.supermodel import model
from zope.component import getUtility
from zope.interface import implements
from zope.interface import Invalid


class RestrictedNamedBlobFile(NamedBlobFile):
    def _validate(self, value):
        super(RestrictedNamedBlobFile, self)._validate(value)
        if value is not None:
            # we are editing the dmsmainfile, there was previously another type, we keep it !
            # It's necessary to permit edition of a pdf scanned file
            if (
                self.context.portal_type == "dmsommainfile"
                and self.context.file.contentType != "application/vnd.oasis.opendocument.text"
            ):
                return
            registry = getUtility(IRegistry)
            allowed_file_formats = registry.get('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_formats_mainfile')
            mimetype = get_contenttype(value)
            if mimetype not in allowed_file_formats:
                raise Invalid(_('Invalid file format. Allowed formats are: ${formats}.',
                                mapping={'formats': ', '.join([v.title for v in OMFileFormatsVocabulary()(None)])}))


class IImioDmsFile(IDmsFile):
    """Schema for DmsFile"""

    model.primary("file")
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

    def getFile(self):
        # documentgenerator compliancy before plone 5
        return self.file

    def is_odt(self):
        return self.file.contentType == "application/vnd.oasis.opendocument.text"


class ImioDmsFileSchemaPolicy(DexteritySchemaPolicy):
    """Schema Policy for DmsFile"""

    def bases(self, schemaName, tree):
        return (IImioDmsFile,)
