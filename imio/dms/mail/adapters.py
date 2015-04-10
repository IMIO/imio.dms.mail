# encoding: utf-8
from collections import OrderedDict
from plone import api

review_levels = {'dmsincomingmail': OrderedDict([('dir_general', {'st': 'proposed_to_manager'}),
                                                 ('_validateur', {'st': 'proposed_to_service_chief',
                                                                  'org': 'treating_groups'})])}


def highest_review_level(portal_type, group_ids):
    """ Return the first review level """
    if portal_type not in review_levels:
        return None
    for keyg in review_levels[portal_type].keys():
        if keyg.startswith('_') and "%s'" % keyg in group_ids:
            return keyg
        elif "'%s'" % keyg in group_ids:
            return keyg
    return None


class IncomingMailHighestValidationCriterionFilterAdapter(object):

    def __init__(self, context):
        self.context = context

    @property
    def query(self):
        groups = api.group.get_groups(user=api.user.get_current())
        highest_level = highest_review_level('dmsincomingmail', str([g.id for g in groups]))
        if highest_level is None:
            return {}
        ret = {}
        criterias = review_levels['dmsincomingmail'][highest_level]
        if 'st' in criterias:
            ret['review_state'] = criterias['st']
        if 'org' in criterias:
            organizations = []
            for group in groups:
                if group.id.endswith(highest_level):
                    organizations.append(group.id[:-len(highest_level)])
            ret[criterias['org']] = organizations
        return ret
