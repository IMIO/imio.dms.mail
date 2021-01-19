# -*- coding: utf-8 -*-

from dexterity.localrolesfield.field import LocalRoleField
from imio.dms.mail import _
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.vocabularies import ActiveCreatingGroupVocabulary
from plone import api
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from zope.interface import alsoProvides
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory


@provider(IContextAwareDefaultFactory)
def user_creating_group(context):
    """ default to current user creating group """
    voc = ActiveCreatingGroupVocabulary()(context)
    creating_groups = set([term.value for term in voc])
    if not creating_groups:
        return None
    user = api.user.get_current()
    # user is anonymous when some widget are accessed in source search or masterselect
    # check if we have a real user to avoid 404 because get_groups on None user
    if user.getId():
        user_groups = api.group.get_groups(user=api.user.get_current())
        # we check if user is in creating_group for incoming and contact_part for outgoing and contact
        for fct in (CREATING_GROUP_SUFFIX, CONTACTS_PART_SUFFIX):
            user_orgs = set([gp.id[:-14] for gp in user_groups if gp.id.endswith(fct)])
            inter = creating_groups & user_orgs
            if inter:
                # ordered = [uid for uid in creating_groups if uid in inter]; return ordered[0]
                return inter.pop()
    return creating_groups.pop()


class IDmsMailCreatingGroup(model.Schema):

    creating_group = LocalRoleField(
        title=_(u"Creating group"),
        required=True,
        vocabulary=u'imio.dms.mail.ActiveCreatingGroupVocabulary',
        defaultFactory=user_creating_group,
    )

    # directives.write_permission(creating_group='imio.dms.mail.write_creating_group_field')
    directives.write_permission(creating_group='imio.dms.mail.write_base_fields')


alsoProvides(IDmsMailCreatingGroup, IFormFieldProvider)
