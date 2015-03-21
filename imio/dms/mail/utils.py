# encoding: utf-8
from plone import api
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm


def voc_selected_org_suffix_users(org_uid, suffixes):
    """
        Get users that belongs to suffixed groups related to selected organization.
    """
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
