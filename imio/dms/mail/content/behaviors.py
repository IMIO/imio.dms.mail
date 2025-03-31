# -*- coding: utf-8 -*-
from collective.contact.plonegroup.utils import get_person_from_userid
from dexterity.localrolesfield.field import LocalRoleField
from imio.dms.mail import _
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.vocabularies import ActiveCreatingGroupVocabulary
from imio.helpers.cache import get_plone_groups_for_user
from plone import api
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from zope.interface import alsoProvides
from zope.schema import Text


def default_creating_group(user=None):
    """default to current user creating group"""
    voc = ActiveCreatingGroupVocabulary()(None)
    creating_groups = set([term.value for term in voc])
    if not creating_groups:
        return None
    if user is None:
        user = api.user.get_current()
    # user is anonymous when some widget are accessed in source search or masterselect
    # check if we have a real user to avoid 404 because get_groups on None user
    if user.getId():
        user_groups = get_plone_groups_for_user(user=user)
        # we check if user is in creating_group for incoming and contact_part for outgoing and contact
        for fct in (CREATING_GROUP_SUFFIX, CONTACTS_PART_SUFFIX):
            user_orgs = set([gp[:-14] for gp in user_groups if gp.endswith(fct)])
            inter = creating_groups & user_orgs
            if inter:
                pers = get_person_from_userid(user.getId())
                if pers and pers.primary_organization and pers.primary_organization in inter:
                    return pers.primary_organization
                ordered = [uid for uid in [term.value for term in voc] if uid in inter]
                return ordered[0]
    return [term.value for term in voc][0]  # take the first term (following plonegroup-organization items order)


class IDmsMailCreatingGroup(model.Schema):

    creating_group = LocalRoleField(
        title=_(u"Creating group"),
        required=True,
        vocabulary=u"imio.dms.mail.ActiveCreatingGroupVocabulary",
        defaultFactory=default_creating_group,
    )

    # directives.write_permission(creating_group='imio.dms.mail.write_creating_group_field')
    # if set, the field is not visible at creation: we handle this in edit form
    # directives.write_permission(creating_group="imio.dms.mail.write_base_fields")


alsoProvides(IDmsMailCreatingGroup, IFormFieldProvider)


class IDmsMailDataTransfer(model.Schema):

    data_transfer = Text(
        title=_(u"Data transfer"),
        required=False,
        #        readonly=True,
    )
    directives.write_permission(data_transfer="cmf.ManagePortal")


alsoProvides(IDmsMailDataTransfer, IFormFieldProvider)
