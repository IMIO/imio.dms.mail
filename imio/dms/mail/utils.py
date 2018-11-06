# encoding: utf-8

from browser.settings import IImioDmsMailConfig
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.utils import organizations_with_suffixes
from datetime import date
from datetime import timedelta
from imio.dashboard.utils import getCurrentCollection
from imio.helpers.cache import generate_key
from imio.helpers.cache import get_cachekey_volatile
from interfaces import IIMDashboard
from natsort import natsorted
#from operator import itemgetter
from persistent.list import PersistentList
from persistent.dict import PersistentDict
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import getToolByName
from Products.CPUtils.Extensions.utils import check_zope_admin
from Products.Five import BrowserView
from zope.annotation.interfaces import IAnnotations
from zope.component import getUtility
from zope.component.hooks import getSite
from zope.schema.interfaces import IVocabularyFactory

import logging


# methods

logger = logging.getLogger('imio.dms.mail: utils')


def set_dms_config(keys=None, value='list'):
    """
        Set initial value in 'imio.dms.mail' portal annotation.
        keys is the chain of annotation keys. First key 'imio.dms.mail' is implicitly added.
        Intermediate keys will contain PersistentDict.
        Last key will contain PersistentDict or PersistentList following 'value' parameter:
        'dict', 'list' or directly value
    """
    annot = IAnnotations(api.portal.get())
    if keys is None:
        keys = []
    keys.insert(0, 'imio.dms.mail')
    last = len(keys) - 1
    for i, key in enumerate(keys):
        if i < last:
            annot = annot.setdefault(key, PersistentDict())
        else:
            if value == 'list':
                annot[key] = PersistentList()
            elif value == 'dict':
                annot[key] = PersistentDict()
            else:
                annot[key] = value
            return annot[key]


def get_dms_config(keys=None):
    """
        Return annotation value from keys list.
        First key 'imio.dms.mail' is implicitly added.
    """
    annot = IAnnotations(api.portal.get())
    if keys is None:
        keys = []
    keys.insert(0, 'imio.dms.mail')
    for key in keys:
        annot = annot[key]
    return annot


def highest_review_level(portal_type, group_ids):
    """ Return the first review level """
    review_levels = get_dms_config(['review_levels'])
    if portal_type not in review_levels:
        return None
    for keyg in review_levels[portal_type].keys():
        if keyg.startswith('_') and "%s'" % keyg in group_ids:
            return keyg
        elif "'%s'" % keyg in group_ids:
            return keyg
    return None


def list_wf_states_cache_key(function, context, portal_type):
    return get_cachekey_volatile("%s.%s" % (generate_key(function), portal_type))


@ram.cache(list_wf_states_cache_key)
def list_wf_states(context, portal_type):
    """
        list all portal_type wf states
    """
    ordered_states = {
        'dmsincomingmail': ['created', 'proposed_to_pre_manager', 'proposed_to_manager', 'proposed_to_service_chief',
                            'proposed_to_agent', 'in_treatment', 'closed'],
        'task': ['created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed'],
        'dmsoutgoingmail': ['scanned', 'created', 'proposed_to_service_chief', 'to_print', 'to_be_signed', 'sent'],
        'organization': ['active', 'deactivated'],
        'person': ['active', 'deactivated'],
        'held_position': ['active', 'deactivated'],
        'contact_list': ['active', 'deactivated'],
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


def back_or_again_state(obj, transitions=[]):
    """
        p_transitions : list of back transitions
    """
    with api.env.adopt_roles(['Manager']):
        history = obj.portal_workflow.getInfoFor(obj, 'review_history')
    # action can be None if initial state or automatic transition
# [{'action': None, 'review_state': 'created', 'comments': '', 'actor': 'admin', 'time': DateTime()}, ...]
    if transitions and history[-1]['action'] in transitions:
        return 'back'
    if history[-1]['action'] and history[-1]['action'].startswith('back_'):
        return 'back'
    i = 0
    last_state = history[-1]['review_state']
    for event in history:
        if event['review_state'] == last_state:
            i = i + 1
            if i > 1:
                break
    else:
        return ''  # no break
    return 'again'


def object_modified_cachekey(method, self, brain=False):
    ''' cachekey method for an object and his modification date. '''
    return (self, self.modified())


# Moved to imio.helpers
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
        brains = pc.unrestrictedSearchResults(portal_type=self.mainfile_type, sort_on='scan_id',
                                              sort_order='descending')
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


class VariousUtilsMethods(UtilsMethods):
    """ View containing various utils methods """

    def initialize_service_folder(self):
        """ """
        if not self.user_is_admin() and not check_zope_admin():
            return
        portal = api.portal.get()
        om_folder = portal['templates']['om']
        base_model = om_folder.get('main', None)
        if not base_model:
            return
        brains = portal.portal_catalog(portal_type='Folder', path={'query': '/'.join(om_folder.getPhysicalPath()),
                                                                   'depth': 1})
        for brain in brains:
            folder = brain.getObject()
            contents = api.content.find(context=folder, depth=1)
            if not contents:
                logger.info("Copying %s in %s" % (base_model, brain.getPath()))
                api.content.copy(source=base_model, target=folder)
        return self.context.REQUEST['RESPONSE'].redirect(self.context.absolute_url())

    def unread_criteria(self):
        """ """
        cc = getCurrentCollection(self.context)
        if not cc or cc.id != 'in_copy_unread':
            return 'FACET-EMPTY'
        user = api.user.get_current()
        return {'not': '%s:lu' % user.id}

    def check_scan_id(self, by='1000', sort='scan'):
        """ Return a list of scan ids, one by 1000 items and by flow types """
        import os
        res = {'0': {}, '1': {}, '2': {}}
        flow_titles = {'0': u'Courrier entrant', '1': u'Courrier sortant', '2': u'Courrier sortant généré'}
        pc = getToolByName(self.context, 'portal_catalog')
        brains = pc.unrestrictedSearchResults(portal_type=['dmsmainfile', 'dmsommainfile'])
        divisor = int(by)
        out = []
        for brain in brains:
            if not brain.scan_id:
                continue
            nb = int(brain.scan_id[7:])
            if (nb % divisor) == 0:
                ref = brain.getObject().__parent__.internal_reference_no
                if sort == 'scan':
                    res[brain.scan_id[2:3]][nb] = (os.path.dirname(brain.getURL()), ref)
                else:
                    res[brain.scan_id[2:3]][ref] = (os.path.dirname(brain.getURL()), nb)
        for flow in sorted(res):
            out.append("<h1>%s</h1>" % flow_titles[flow])
            for nb in natsorted(res[flow], reverse=True):
                out.append('<a href="%s" target="_blank">%s</a>, %s' % (res[flow][nb][0], nb, res[flow][nb][1]))
        return '<br/>\n'.join(out)

    def pg_organizations(self, only_activated='1', output='csv', with_status=''):
        """ Return a list of tuples with plonegroup organizations """
        factory = getUtility(IVocabularyFactory, 'collective.contact.plonegroup.organization_services')
        lst = []
        registry = getUtility(IRegistry)
        activated = registry[ORGANIZATIONS_REGISTRY]
        for term in factory(self.context):
            uid, title = term.value, term.title
            status = uid in activated and 'a' or 'na'
            if only_activated and status == 'na':
                continue
            lst.append((uid, title.encode('utf8'), status))
        #sorted(lst, key=itemgetter(1))
        if output != 'csv':
            return lst
        ret = []
        for uid, tit, stat in lst:
            if with_status:
                ret.append('%s;%s;%s' % (uid, tit, stat))
            else:
                ret.append('%s;%s' % (uid, tit))
        return '\n'.join(ret)


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

    def proposed_to_pre_manager_col_cond(self):
        """ Condition for searchfor_proposed_to_pre_manager collection """
        return self.is_in_user_groups(['encodeurs', 'dir_general', 'pre_manager'], admin=False)

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
        return "{}/#c3=20&b_start=0&c1={}&c10={}&c10={}".format(url, col_uid, from_date.strftime('%Y-%m-%d'),
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


class Dummy(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
