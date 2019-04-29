# -*- coding: utf-8 -*-

from dexterity.localrolesfield.field import LocalRoleField
from imio.dms.mail import _
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.indexer import indexer
from plone.supermodel import model
from Products.CMFPlone.utils import base_hasattr
from Products.PluginIndexes.common.UnIndex import _marker
from zope.interface import alsoProvides


class IDmsMailCreatingGroup(model.Schema):

    creating_group = LocalRoleField(
        title=_(u"Creating group"),
        required=True,
        vocabulary=u'imio.dms.mail.ActiveCreatingGroupVocabulary'
    )

#    directives.read_permission(creating_group='imio.dms.mail: Write creating group field')
    directives.write_permission(creating_group='imio.dms.mail: Write creating group field')

alsoProvides(IDmsMailCreatingGroup, IFormFieldProvider)


@indexer(IDmsMailCreatingGroup)
def creating_group_indexer(obj):
    """
        indexer method
    """
    if base_hasattr(obj, 'creating_group') and obj.creating_group:
        return obj.creating_group
    return _marker
