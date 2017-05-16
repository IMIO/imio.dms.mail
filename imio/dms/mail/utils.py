# encoding: utf-8

from datetime import date, timedelta
from operator import methodcaller
from collections import OrderedDict

from zope.component.hooks import getSite
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.component import getUtility

from plone import api
from plone.app.textfield.value import RichTextValue
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import getToolByName
from Products.Five import BrowserView

from collective.contact.plonegroup.utils import organizations_with_suffixes
from imio.helpers.cache import get_cachekey_volatile, generate_key
from browser.settings import IImioDmsMailConfig
from interfaces import IIMDashboard

# methods

review_levels = {'dmsincomingmail': OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                                 ('_validateur', {'st': ['proposed_to_service_chief'],
                                                                  'org': 'treating_groups'})]),
                 'task': OrderedDict([('_validateur', {'st': ['to_assign', 'realized'],
                                                       'org': 'assigned_group'})]),
                 'dmsoutgoingmail': OrderedDict([('_validateur', {'st': ['proposed_to_service_chief'],
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


def get_selected_org_suffix_users(org_uid, suffixes):
    """
        Get users that belongs to suffixed groups related to selected organization.
    """
    org_members = []
    # only add to vocabulary users with these functions in the organization
    for function_id in suffixes:
        groupname = "{}_{}".format(org_uid, function_id)
        members = api.user.get_users(groupname=groupname)
        for member in members:
            if member not in org_members:
                org_members.append(member)
    return org_members


def voc_selected_org_suffix_users(org_uid, suffixes, first_member=None):
    """
        Return users vocabulary that belongs to suffixed groups related to selected organization.
    """
    if not org_uid or org_uid == u'--NOVALUE--':
        return SimpleVocabulary([])
    terms = []
    # only add to vocabulary users with these functions in the organization
    for member in sorted(get_selected_org_suffix_users(org_uid, suffixes), key=methodcaller('getUserName')):
        if member == first_member:
            terms.insert(0, SimpleTerm(
                value=member.getUserName(),  # login
                token=member.getId(),  # id
                title=member.getUser().getProperty('fullname') or member.getUserName()))
        else:
            terms.append(SimpleTerm(
                value=member.getUserName(),  # login
                token=member.getId(),  # id
                title=member.getUser().getProperty('fullname') or member.getUserName()))  # title
    return SimpleVocabulary(terms)


def list_wf_states_cache_key(function, context, portal_type):
    return get_cachekey_volatile("%s.%s" % (generate_key(function), portal_type))


@ram.cache(list_wf_states_cache_key)
def list_wf_states(context, portal_type):
    """
        list all portal_type wf states
    """
    ordered_states = {
        'dmsincomingmail': ['created', 'proposed_to_manager', 'proposed_to_service_chief',
                            'proposed_to_agent', 'in_treatment', 'closed'],
        'task': ['created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed'],
        'dmsoutgoingmail': ['scanned', 'created', 'proposed_to_service_chief', 'to_be_signed', 'sent']
    }
    if portal_type not in ordered_states:
        return []
    pw = api.portal.get_tool('portal_workflow')
    ret = []
    # wf states
    for workflow in pw.getWorkflowsFor(portal_type):
        states = dict([(value.id, value) for value in workflow.states.values()])
        break
    # keep ordered states
    for state in ordered_states[portal_type]:
        if state in states:
            ret.append(states[state])
            del(states[state])
    # add missing
    for missing in states:
        ret.append(states[missing])
    return ret


# May be moved to imio.helpers ?
def create_richtextval(text):
    """ Return a RichTextValue """
    if not isinstance(text, unicode):
        text = text.decode('utf8')
    return RichTextValue(raw=text, mimeType='text/html', outputMimeType='text/html', encoding='utf-8')


def get_scan_id(obj):
    """ Return scan_id in multiple form """
    sid = (obj.scan_id and obj.scan_id.startswith('IMIO') and obj.scan_id[4:] or obj.scan_id)
    sid_long, sid_short = '', ''
    if sid:
        sid_long = u"IMIO%s" % sid
        sid_short = (len(sid) == 15 and sid[7:].lstrip('0') or sid)
    return [sid, sid_long, sid_short]


# views

class UtilsMethods(BrowserView):
    """ View containing utils methods """
    mainfile_type = 'dmsmainfile'

    def user_is_admin(self):
        """ Test if current user is admin """
        user = api.user.get_current()
        if user.has_role(['Manager', 'Site Administrator']):
            return True
        return False

    def current_user_groups(self, user):
        """ Return current user groups """
        return api.group.get_groups(user=user)

    def current_user_groups_ids(self, user):
        """ Return current user groups ids """
        return [g.id for g in self.current_user_groups(user)]

    def highest_scan_id(self):
        """ Return highest scan id """
        pc = getToolByName(self.context, 'portal_catalog')
        brains = pc(portal_type=self.mainfile_type, sort_on='scan_id', sort_order='descending')
        if brains:
            return "dmsmainfiles: '%d', highest scan_id: '%s'" % (len(brains), brains[0].scan_id)
        else:  # pragma: no cover
            return 'No scan id'

    def is_in_user_groups(self, groups=[], admin=True, test='any'):
        """ Test if one or all of a given group list is part of the current user groups """
        # for admin, we bypass the check
        if admin and self.user_is_admin():
            return True
        u_groups = self.current_user_groups_ids(api.user.get_current())
        if test == 'any':
            return any(x in u_groups for x in groups)
        elif test == 'all':
            return all(x in u_groups for x in groups)
        return False

    def user_has_review_level(self, portal_type=None):
        """ Test if the current user has a review level """
        if portal_type is None:
            portal_type = self.context.portal_type
        if highest_review_level(portal_type, str(self.current_user_groups_ids(api.user.get_current()))) is not None:
            return True
        else:
            return False


class IdmUtilsMethods(UtilsMethods):
    """ View containing incoming mail utils methods """

    def get_im_folder(self):
        """ Get the incoming-mail folder """
        portal = getSite()
        return portal['incoming-mail']

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
        return self.is_in_user_groups(['encodeurs'], admin=False)

    def proposed_to_manager_col_cond(self):
        """ Condition for searchfor_proposed_to_manager collection """
        return self.is_in_user_groups(['encodeurs', 'dir_general'], admin=False)

    def proposed_to_serv_chief_col_cond(self):
        """ Condition for searchfor_proposed_to_service_chief collection """
        if self.is_in_user_groups(['encodeurs', 'dir_general'], admin=False) or \
                organizations_with_suffixes(self.current_user_groups(api.user.get_current()), ['validateur']):
            return True
        return False

    def must_render_im_listing(self):
        if IIMDashboard.providedBy(self.context):
            return True
        return False

    def im_listing_url(self):
        col_folder = self.get_im_folder()['mail-searches']
        url = col_folder.absolute_url()
        col_uid = col_folder['all_mails'].UID()
        from_date = date.today()
        to_date = from_date + timedelta(1)
        return "{}/#c3=500&b_start=0&c1={}&c10={}&c10={}".format(url, col_uid, from_date.strftime('%Y-%m-%d'),
                                                                 to_date.strftime('%Y-%m-%d'))


class OdmUtilsMethods(UtilsMethods):
    """ View containing outgoing mail utils methods """
    mainfile_type = 'dmsommainfile'

    def get_om_folder(self):
        """ Get the outgoing-mail folder """
        portal = getSite()
        return portal['outgoing-mail']

    def scanned_col_cond(self):
        """ Condition for searchfor_scanned collection """
        return self.is_in_user_groups(['encodeurs', 'expedition'], admin=False)

    def is_odt_activated(self):
        registry = getUtility(IRegistry)
        return registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile']
