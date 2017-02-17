# -*- coding: utf-8 -*-
"""Example."""
from zope import schema
from zope.interface import Interface

from plone import api

from collective.wfadaptations.wfadaptation import WorkflowAdaptationBase


class IEmergencyZoneParameters(Interface):

    manager_suffix = schema.TextLine(
        title=u"Manager suffix",
        default=u'_zs',
        required=True)


class EmergencyZoneAdaptation(WorkflowAdaptationBase):

    schema = IEmergencyZoneParameters

    def patch_workflow(self, workflow_name, **parameters):
        portal = api.portal.get()
        wtool = portal.portal_workflow
        # change state title.
        im_workflow = wtool['incomingmail_workflow']
        msg = self.check_state_in_workflow(im_workflow, 'proposed_to_manager')
        if msg:
            return False, msg
        state = im_workflow.states['proposed_to_manager']
        new_title = "proposed_to_manager%s" % parameters['manager_suffix']
        if state.title != new_title:
            state.title = str(new_title)

        # change transition title.
        for tr in ('back_to_manager', 'propose_to_manager'):
            msg = self.check_transition_in_workflow(im_workflow, tr)
            if msg:
                return False, msg
            transition = im_workflow.transitions[tr]
            new_title = "%s%s" % (tr, parameters['manager_suffix'])
            if transition.title != new_title:
                transition.title = str(new_title)

        # change collection title
        collection = portal.restrictedTraverse('incoming-mail/mail-searches/searchfor_proposed_to_manager',
                                               default=None)
        if not collection:
            return False, "'incoming-mail/mail-searches/searchfor_proposed_to_manager' not found"
        if collection.Title().endswith(' DG'):
            collection.setTitle(collection.Title().replace(' DG', ' CZ'))
            collection.reindexObject(['Title', 'SearchableText'])
        return True, ''
