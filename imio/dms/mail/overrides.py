# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from collective.contact.core.content.person import IPerson
from collective.contact.plonegroup.subscribers import PloneGroupContactChecksAdapter
from collective.contact.plonegroup.subscribers import search_value_in_objects
from collective.z3cform.chosen.widget import AjaxChosenFieldWidget
from imio.dms.mail import _
from plone.autoform import directives
from plone.dexterity.schema import DexteritySchemaPolicy
from zope import schema


class IDmsPerson(IPerson):

    userid = schema.Choice(
        title=_(u'Plone user'),
        required=False,
        vocabulary=u'plone.app.vocabularies.Users',
    )

    #directives.widget('userid', AjaxChosenFieldWidget, populate_select=True)
    directives.read_permission(userid='imio.dms.mail.write_userid_field')
    directives.write_permission(userid='imio.dms.mail.write_userid_field')


class DmsPersonSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IDmsPerson, )


class DmsPloneGroupContactChecksAdapter(PloneGroupContactChecksAdapter):

    def check_items_on_delete(self):
        fields = {'dmsincomingmail': ['treating_groups', 'recipient_groups'],
                  'dmsincoming_email': ['treating_groups', 'recipient_groups'],
                  'dmsoutgoingmail': ['treating_groups', 'recipient_groups'],
                  'task': ['assigned_group', 'enquirer', 'parents_assigned_groups', 'parents_enquirers']}
        search_value_in_objects(self.context, self.context.UID(), p_types=fields.keys(), type_fields=fields)

    def check_items_on_transition(self):
        fields = {'dmsincomingmail': ['treating_groups', 'recipient_groups'],
                  'dmsincoming_email': ['treating_groups', 'recipient_groups'],
                  'dmsoutgoingmail': ['treating_groups', 'recipient_groups'],
                  'task': ['assigned_group', 'enquirer', 'parents_assigned_groups', 'parents_enquirers']}
        search_value_in_objects(self.context, self.context.UID(), p_types=fields.keys(), type_fields=fields)
