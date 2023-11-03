# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from collective.contact.core.content.person import IPerson
from collective.contact.plonegroup.subscribers import PloneGroupContactChecksAdapter
from collective.contact.plonegroup.subscribers import search_value_in_objects
from collective.task.adapters import TaskContentAdapter
from imio.dms.mail import _
from imio.dms.mail.utils import get_dms_config
from plone import api
from plone.autoform import directives
from plone.dexterity.schema import DexteritySchemaPolicy
from zope import schema


# TODO: must be removed soon !!
class IDmsPerson(IPerson):

    userid = schema.Choice(
        title=_(u'Plone user'),
        required=False,
        vocabulary=u'plone.app.vocabularies.Users',
    )

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


class DmsTaskContentAdapter(TaskContentAdapter):
    security = ClassSecurityInfo()

    security.declarePublic('can_do_transition')

    def can_do_transition(self, transition):
        """Check if assigned_user is set or if the test is required or if the user is admin.
        Used in guard expression for n+1 related task transitions
        """
        if self.context.assigned_group is None:
            # print "no tg: False"
            return False
        way_index = transition.startswith('back_in') and 1 or 0
        # show only the next valid level
        state = api.content.get_state(self.context)
        transitions_levels = get_dms_config(['transitions_levels', 'task'])
        if (self.context.assigned_group in transitions_levels[state] and
           transitions_levels[state][self.context.assigned_group][way_index] == transition):
            # print "from state: True"
            return True
        return False


InitializeClass(DmsTaskContentAdapter)
