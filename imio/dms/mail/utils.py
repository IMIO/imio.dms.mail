# encoding: utf-8
from plone import api
from Products.Five import BrowserView
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from adapters import highest_review_level


class IdmUtilsMethods(BrowserView):
    """ View containing utils methods """

    def user_has_review_level(self, portal_type):
        """ Test if the current user has a review level """
        user = api.user.get_current()
        groups = api.group.get_groups(user=user)
        if portal_type is None:
            portal_type = self.context.portal_type
        if highest_review_level(portal_type, str([g.id for g in groups])) is not None or \
                user.has_role('Manager'):
            return True
        else:
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
