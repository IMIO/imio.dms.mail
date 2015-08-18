# encoding: utf-8
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.component import getUtility
from plone import api
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import getToolByName
from Products.Five import BrowserView
from adapters import highest_review_level, organizations_with_suffixes
from browser.settings import IImioDmsMailConfig


class UtilsMethods(BrowserView):
    """ View containing utils methods """

    def user_is_admin(self):
        """ Test if current user is admin """
        user = api.user.get_current()
        if user.has_role('Manager') or user.has_role('Site Administrator'):
            return True
        return False

    def current_user_groups(self):
        """ Return current user groups """
        return api.group.get_groups(user=api.user.get_current())

    def highest_scan_id(self):
        """ Return highest scan id """
        pc = getToolByName(self.context, 'portal_catalog')
        brains = pc(portal_type='dmsmainfile', sort_on='scan_id', sort_order='descending', sort_limit=1)
        if brains:
            return brains[0].scan_id
        else:
            return 'No scan id'


class IdmUtilsMethods(UtilsMethods):
    """ View containing incoming mail utils methods """

    def user_has_review_level(self, portal_type=None):
        """ Test if the current user has a review level """
        groups = self.current_user_groups()
        if portal_type is None:
            portal_type = self.context.portal_type
        if highest_review_level(portal_type, str([g.id for g in groups])) is not None:
            return True
        else:
            return False

    def idm_has_assigned_user(self):
        """ Test if assigned_user is set or if the test is required or if the user is admin """
        if self.context.assigned_user is not None:
            return True
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if not settings.assigned_user_check:
            return True
        if self.user_is_admin():
            return True
        return False

    def created_col_cond(self):
        """ Condition for searchfor_created collection """
        if 'encodeurs' in self.current_user_groups():
            return True
        return False

    def proposed_to_manager_col_cond(self):
        """ Condition for searchfor_proposed_to_manager collection """
        if 'dir_general' in self.current_user_groups():
            return True
        return False

    def proposed_to_serv_chief_col_cond(self):
        """ Condition for searchfor_proposed_to_service_chief collection """
        if organizations_with_suffixes(self.current_user_groups(), ['validateur']):
            return True
        return False


def voc_selected_org_suffix_users(org_uid, suffixes):
    """
        Get users that belongs to suffixed groups related to selected organization.
    """
    if not org_uid or org_uid == u'--NOVALUE--':
        return SimpleVocabulary([])
    terms = []
    already_added = []
    # only add to vocabulary users with these functions in the organization
    for function_id in suffixes:
        groupname = "{}_{}".format(org_uid, function_id)
        members = api.user.get_users(groupname=groupname)
        for member in members:
            member_id = member.getId()
            if member_id not in already_added:
                title = member.getUser().getProperty('fullname') or member_id
                terms.append(SimpleTerm(
                    value=member.getUserName(),  # login
                    token=member_id,  # id
                    title=title))  # title
                already_added.append(member_id)
    return SimpleVocabulary(terms)
