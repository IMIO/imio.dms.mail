# -*- coding: utf-8 -*-

from dexterity.localrolesfield.field import LocalRoleField
from imio.dms.mail import _
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.vocabularies import ActiveCreatingGroupVocabulary
from plone import api
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.indexer import indexer
from plone.supermodel import model
from Products.CMFPlone.utils import base_hasattr
from Products.PluginIndexes.common.UnIndex import _marker
from zope.interface import alsoProvides
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


@provider(IContextAwareDefaultFactory)
def user_creating_group(context):
    """ default to current user creating group """
    voc = ActiveCreatingGroupVocabulary()(context)
    creating_groups = [term.value for term in voc]
    if not creating_groups:
        return None
    user = api.user.get_current()
    # user is anonymous when some widget are accessed in source search or masterselect
    # check if we have a real user to avoid 404 because get_groups on None user
    if user.getId():
        print user.getId()
        user_groups = set([gp.id[:-14] for gp in api.group.get_groups(user=api.user.get_current()) if
                           gp.id.endswith(CREATING_GROUP_SUFFIX)])
        inter = set(creating_groups) & user_groups
        if inter:
            # ordered = [uid for uid in creating_groups if uid in inter]; return ordered[0]
            return inter.pop()
    return creating_groups[0]


class IDmsMailCreatingGroup(model.Schema):

    creating_group = LocalRoleField(
        title=_(u"Creating group"),
        required=True,
        vocabulary=u'imio.dms.mail.ActiveCreatingGroupVocabulary',
        defaultFactory=user_creating_group,
    )

    # directives.write_permission(creating_group='imio.dms.mail: Write creating group field')
    directives.write_permission(creating_group='imio.dms.mail: Write mail base fields')


alsoProvides(IDmsMailCreatingGroup, IFormFieldProvider)


@indexer(IDmsMailCreatingGroup)
def creating_group_indexer(obj):
    """
        indexer method
    """
    if base_hasattr(obj, 'creating_group') and obj.creating_group:
        return obj.creating_group
    return _marker
