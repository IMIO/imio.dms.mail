# encoding: utf-8

from collective.contact.plonegroup.config import get_registry_organizations
from collective.eeafaceted.collectionwidget.utils import _updateDefaultCollectionFor
from collective.eeafaceted.collectionwidget.utils import getCurrentCollection
from collective.wfadaptations.api import get_applied_adaptations
from datetime import date
from datetime import timedelta
from imio.dms.mail import _tr as _
from imio.dms.mail import AUC_RECORD
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.helpers.cache import generate_key
from imio.helpers.cache import get_cachekey_volatile
from interfaces import IIMDashboard
from natsort import natsorted
from persistent.dict import PersistentDict
from persistent.list import PersistentList
from plone import api
from plone.api.exc import GroupNotFoundError
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
import os

cg_separator = ' ___ '

# methods

logger = logging.getLogger('imio.dms.mail: utils')

"""
dms_config
----------
(not the default values! but possible values to illustrate)
* ['wf_from_to'] : états précédant/suivant un autre et transitions pour y accéder
    * ['dmsincomingmail', 'n_plus', 'from'] = [('created', 'back_to_creation'),
                                               ('proposed_to_manager', 'back_to_manager')]
    * ['dmsincomingmail', 'n_plus', 'to'], [('proposed_to_agent', 'propose_to_agent')])
    * ['dmsoutgoingmail', 'n_plus', 'from'], [('created', 'back_to_creation')])
    * ['dmsoutgoingmail', 'n_plus', 'to'], [('to_be_signed', 'propose_to_be_signed')])
* ['review_levels'] : sert à déterminer le niveau de validation d'un utilisateur suivant son groupe
    * ['dmsincomingmail'] = OrderedDict([('dir_general', {'st': ['proposed_to_manager']}),
                                         ('_n_plus_1', {'st': ['proposed_to_n_plus_1'], 'org': 'treating_groups'})])
    * ['task'] = OrderedDict([('_n_plus_1', {'st': ['to_assign', 'realized'], 'org': 'assigned_group'})])
    * ['dmsoutgoingmail'] = OrderedDict([('_n_plus_1', {'st': ['proposed_to_n_plus_1'],
                                                        'org': 'treating_groups'})])
* ['review_states'] : pour l'index state_group, lié à la validation
    * ['dmsincomingmail'] = OrderedDict([('proposed_to_manager', {'group': 'dir_general'}),
                                         ('proposed_to_n_plus_1', {'group': ['_n_plus_1'], 'org': 'treating_groups'})])
    * ['task'] = OrderedDict([('to_assign', {'group': '_n_plus_1', 'org': 'assigned_group'}),
                                ('realized', {'group': '_n_plus_1', 'org': 'assigned_group'})])
    * ['dmsoutgoingmail'] = OrderedDict([('proposed_to_n_plus_1', {'group': '_n_plus_1', 'org': 'treating_groups'})])
* ['transitions_auc'] : indique si les transitions propose_to_agent ou propose_to_n_plus_x peuvent être effectuées en
                        fonction du paramètre assigned_user_check
    * ['dmsincomingmail'][transition] = {'org1': True, 'org2': False}
* ['transitions_levels'] : indique les transitions valides par état en fonction de la présence des validateurs
    * ['dmsincomingmail'][state] = {'org1': ('propose_to_n_plus_1', 'from_states'), 'org2': (...) }
    ('from_states' est une valeur spéciale qui représente les transitions stockées dans from_states)
"""


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


def group_has_user(groupname, action=None):
    """ Check if group contains user """
    try:
        # group is deleted
        if action == 'delete':
            return False
        users_len = len(api.user.get_users(groupname=groupname))
        if action == 'remove' and users_len == 1:
            return False
        elif action == 'add' and users_len == 0:
            return True
        elif users_len:
            return True
    except GroupNotFoundError:
        return False
    return False


def update_transitions_levels_config(ptypes, action=None, group_id=None):
    """
    Set transitions_levels dms config following org group users: [ptype][state][org] = (valid_propose_to, valid_back_to)
    :param ptypes: portal types
    :param action: useful on group assignment event. Can be 'add', 'remove', 'delete'
    :param group_id: new group assignment
    """
    orgs = get_registry_organizations()
    users_in_groups = {}  # boolean by groupname

    def check_group_users(g_n, u_in_g, g_id, act):
        if g_n not in u_in_g:
            u_in_g[g_n] = group_has_user(g_n, action=(g_n == g_id and act or None))
        return u_in_g[g_n]

    if 'dmsincomingmail' in ptypes:
        wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'])
        states = []
        max_level = 0
        for i, (st, tr) in enumerate(wf_from_to['to']):
            states.append((st, i))
            max_level = i
        states += [(st, 9) for (st, tr) in wf_from_to['from']]
        states.reverse()
        state9 = ''
        orgs_back = {}  # last valid back transition by org

        for state, level in states:
            start = level - 1
            if level == 9:
                start = max_level
            # for states before validation levels, we copy the first one
            if level == 9 and state9:
                set_dms_config(['transitions_levels', 'dmsincomingmail', state],
                               get_dms_config(['transitions_levels', 'dmsincomingmail', state9]))
                continue
            config = {}
            for org in orgs:
                propose_to = 'propose_to_agent'
                back_to = orgs_back.setdefault(org, 'from_states')
                # check all lower levels to find first valid propose_to transition
                for lev in range(start, 0, -1):
                    # level 9: range(0, 0, -1) => [] ; range(1, 0, -1) => [1] ; etc.
                    # level 1: range(0, 0, -1) => [] ; level 2: range(1, 0, -1) => [1] ; etc.
                    # level 0: range(-1, 0, -1) => []
                    if check_group_users('{}_n_plus_{}'.format(org, lev), users_in_groups, group_id, action):
                        propose_to = 'propose_to_n_plus_{}'.format(lev)
                        break
                config[org] = (propose_to, back_to)
                if level != 9 and users_in_groups.get('{}_n_plus_{}'.format(org, level), False):
                    orgs_back[org] = 'back_to_n_plus_{}'.format(level)

            set_dms_config(['transitions_levels', 'dmsincomingmail', state], config)
            if level == 9 and not state9:
                state9 = state

    if 'dmsoutgoingmail' in ptypes:
        wf_from_to = get_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus'])
        states = [('created', 0)]
        for (st, tr) in wf_from_to['to']:
            states.append((st, 1))
        right_transitions = ('propose_to_n_plus_1', 'back_to_n_plus_1')
        for st, way in states:
            config = {}
            for org in orgs:
                trs = ['', '']
                if check_group_users('{}_n_plus_1'.format(org), users_in_groups, group_id, action):
                    trs[way] = right_transitions[way]
                config[org] = tuple(trs)
            set_dms_config(['transitions_levels', 'dmsoutgoingmail', st], config)

    if 'task' in ptypes:
        states = (('created', 0), ('to_do', 1))
        right_transitions = ('do_to_assign', 'back_in_to_assign')
        for state, way in states:
            config = {}
            for org in orgs:
                trs = {0: ['', ''], 1: ['', 'back_in_created2']}
                if check_group_users('{}_n_plus_1'.format(org), users_in_groups, group_id, action):
                    trs[way][way] = right_transitions[way]
                config[org] = tuple(trs[way])
            set_dms_config(['transitions_levels', 'task', state], config)


def update_transitions_auc_config(ptype, action=None, group_id=None):
    """
    Set transitions_auc dms config following assigned user check: [ptype][transition][org] = True
    :param ptype: portal type
    :param action: useful on group assignment event. Can be 'add', 'remove', 'delete'
    :param group_id: new group assignment
    """
    orgs = get_registry_organizations()
    if ptype == 'dmsincomingmail':
        auc = api.portal.get_registry_record(AUC_RECORD)
        wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'])
        transitions = [tr for (st, tr) in wf_from_to['to']]
        previous_tr = ''
        global_config = {}
        for i, tr in enumerate(transitions):
            config = {}
            for org in orgs:
                val = False
                if auc == u'no_check':
                    val = True
                elif auc == u'mandatory':
                    # propose_to_agent: previous_tr is empty => val will be False
                    # propose_to_n_plus_x: lower level True => val is True
                    # propose_to_n_plus_x: lower level False and user at this level => val is True
                    groupname = '{}_n_plus_{}'.format(org, i)
                    act = (groupname == group_id and action or None)
                    if previous_tr and (global_config[previous_tr][org] or group_has_user(groupname, action=act)):
                        val = True
                elif auc == u'n_plus_1':
                    # propose_to_agent: no n+1 level => val is True
                    # propose_to_n_plus_x: previous_tr => val is True
                    # propose_to_agent: n+1 level doesn't have user => val is True
                    groupname = '{}_n_plus_1'.format(org)
                    act = (groupname == group_id and action or None)
                    if len(transitions) == 1 or previous_tr or not group_has_user(groupname, action=act):
                        val = True
                config[org] = val
            previous_tr = tr
            global_config[tr] = config
            set_dms_config(['transitions_auc', 'dmsincomingmail', tr], config)


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
        'dmsincomingmail': ['created', 'proposed_to_pre_manager', 'proposed_to_manager', 'proposed_to_n_plus_5',
                            'proposed_to_n_plus_4', 'proposed_to_n_plus_3', 'proposed_to_n_plus_2',
                            'proposed_to_n_plus_1', 'proposed_to_agent', 'in_treatment', 'closed'],
        'dmsincoming_email': ['created', 'proposed_to_pre_manager', 'proposed_to_manager', 'proposed_to_n_plus_5',
                              'proposed_to_n_plus_4', 'proposed_to_n_plus_3', 'proposed_to_n_plus_2',
                              'proposed_to_n_plus_1', 'proposed_to_agent', 'in_treatment', 'closed'],
        'task': ['created', 'to_assign', 'to_do', 'in_progress', 'realized', 'closed'],
        'dmsoutgoingmail': ['scanned', 'created', 'proposed_to_n_plus_1', 'to_print', 'to_be_signed', 'sent'],
        'dmsoutgoing_email': ['scanned', 'created', 'proposed_to_n_plus_1', 'to_print', 'to_be_signed', 'sent'],
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
    states = []
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


def back_or_again_state(obj, transitions=()):
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
    """ cachekey method for an object and his modification date. """
    return self, self.modified()


def get_scan_id(obj):
    """ Return scan_id in multiple form """
    sid = (obj.scan_id and obj.scan_id.startswith('IMIO') and obj.scan_id[4:] or obj.scan_id)
    sid_long, sid_short = '', ''
    if sid:
        sid_long = u"IMIO%s" % sid
        sid_short = (len(sid) == 15 and sid[7:].lstrip('0') or sid)
    return [sid, sid_long, sid_short]


def reimport_faceted_config(folder, xml, default_UID=None):  # noqa
    """Reimport faceted navigation config."""
    folder.unrestrictedTraverse('@@faceted_exportimport').import_xml(
        import_file=open(os.path.dirname(__file__) + '/faceted_conf/%s' % xml))
    if default_UID:
        _updateDefaultCollectionFor(folder, default_UID)


# views

class UtilsMethods(BrowserView):
    """ View containing utils methods """
    mainfile_type = 'dmsmainfile'

    def user_is_admin(self):
        """ Test if current user is admin """
        user = api.user.get_current()
        return user.has_role(['Manager', 'Site Administrator'])

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

    def is_in_user_groups(self, groups=(), admin=True, test='any', suffixes=()):
        """
            Test if one or all of a given group list is part of the current user groups
            Test if one or all of a suffix list is part of the current user groups
        """
        # for admin, we bypass the check
        if admin and self.user_is_admin():
            return True
        u_groups = self.current_user_groups_ids(api.user.get_current())
        u_suffixes = [sfx for sfx in suffixes for grp in u_groups if grp.endswith('_{}'.format(sfx))]
        if test == 'any':
            return any(x in u_groups for x in groups) or any(sfx in u_suffixes for sfx in suffixes)
        elif test == 'all':
            return all(x in u_groups for x in groups) and all(sfx in u_suffixes for sfx in suffixes)
        return False

    def user_has_review_level(self, portal_type=None):
        """ Test if the current user has a review level """
        if portal_type is None:
            portal_type = self.context.portal_type
        return highest_review_level(portal_type, str(self.current_user_groups_ids(api.user.get_current()))) is not None


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
        if not self.user_is_admin() and not check_zope_admin():
            return
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
                ref = brain._unrestrictedGetObject().__parent__.internal_reference_no
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
        if not self.user_is_admin() and not check_zope_admin():
            return
        factory = getUtility(IVocabularyFactory, 'collective.contact.plonegroup.organization_services')
        lst = []
        activated = get_registry_organizations()
        for term in factory(self.context):
            uid, title = term.value, term.title
            status = uid in activated and 'a' or 'na'
            if only_activated == '1' and status == 'na':
                continue
            lst.append((uid, title.encode('utf8'), status))
        # sorted(lst, key=itemgetter(1))
        if output != 'csv':
            return lst
        ret = []
        for uid, tit, stat in lst:
            if with_status:
                ret.append('%s;%s;%s' % (uid, tit, stat))
            else:
                ret.append('%s;%s' % (uid, tit))
        return '\n'.join(ret)

    def kofax_orgs(self):
        """ Return a list of orgs formatted for Kofax """
        if not self.user_is_admin():
            return

        def get_voc_values(voc_name):
            values = []
            factory = getUtility(IVocabularyFactory, voc_name)
            for term in factory(self.context):
                values.append('{}{}{}'.format(term.title.encode('utf8'), cg_separator, term.value))
            return values

        ret = []  # noqa
        ret.append(_('Creating groups : to be used in kofax index').encode('utf8'))
        ret.append('')
        ret.append('\r\n'.join(get_voc_values('imio.dms.mail.ActiveCreatingGroupVocabulary')))
        ret.append('')
        ret.append(_('Treating groups : to be used in kofax index').encode('utf8'))
        ret.append('')
        ret.append('\r\n'.join(get_voc_values('collective.dms.basecontent.treating_groups')))
        return '\r\n'.join(ret)


class IdmUtilsMethods(UtilsMethods):
    """ View containing incoming mail utils methods """

    def get_im_folder(self):
        """ Get the incoming-mail folder """
        portal = getSite()
        return portal['incoming-mail']

    def can_do_transition(self, transition):
        """
            Check if assigned_user is set or if the test is required or if the user is admin.
            Used in guard expression for propose_to_agent transition
        """
        if self.context.treating_groups is None:
            # print "no tg: False"
            return False
        way_index = transition.startswith('back_to') and 1 or 0
        transition_to_test = transition
        wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'])
        if transition in [tr for (st, tr) in wf_from_to['from']]:
            transition_to_test = 'from_states'
        # show only the next valid level
        state = api.content.get_state(self.context)
        transitions_levels = get_dms_config(['transitions_levels', 'dmsincomingmail'])
        if state not in transitions_levels or \
                (transitions_levels[state].get(self.context.treating_groups)
                 and transitions_levels[state][self.context.treating_groups][way_index] != transition_to_test):
            # print "from state: False"
            return False
        # show transition following assigned_user on propose_to transition only
        if way_index == 0:
            if self.context.assigned_user is not None:
                # print "have assigned user: True"
                return True
            transitions_auc = get_dms_config(['transitions_auc', 'dmsincomingmail', transition])
            if transitions_auc.get(self.context.treating_groups, False):
                # print 'auc ok: True'
                return True
        else:
            return True  # state ok, back ok
        return False

    def created_col_cond(self):
        """ Condition for searchfor_created collection """
        return self.is_in_user_groups(['encodeurs'], admin=False, suffixes=[CREATING_GROUP_SUFFIX])

    def proposed_to_manager_col_cond(self):
        """ Condition for searchfor_proposed_to_manager collection """
        return self.is_in_user_groups(['encodeurs', 'dir_general'], admin=False, suffixes=[CREATING_GROUP_SUFFIX])

    def proposed_to_pre_manager_col_cond(self):
        """ Condition for searchfor_proposed_to_pre_manager collection """
        return self.is_in_user_groups(['encodeurs', 'dir_general', 'pre_manager'], admin=False,
                                      suffixes=[CREATING_GROUP_SUFFIX])

    def proposed_to_n_plus_col_cond(self):
        """
            Condition for searchfor_proposed_to_n_plus collection
        """
        suffixes = []
        # a lower level search can be viewed by a higher level
        for i in range(int(self.context.id[-1:]), 6):
            suffixes.append('n_plus_{}'.format(i))
        suffixes.append(CREATING_GROUP_SUFFIX)
        return self.is_in_user_groups(['encodeurs', 'dir_general'], admin=False, suffixes=suffixes)

    def must_render_im_listing(self):
        return IIMDashboard.providedBy(self.context)

    def im_listing_url(self):
        col_folder = self.get_im_folder()['mail-searches']
        url = col_folder.absolute_url()
        col_uid = col_folder['all_mails'].UID()
        from_date = date.today()
        to_date = from_date + timedelta(1)
        return "{}/#c3=20&b_start=0&c1={}&c10={}&c10={}".format(url, col_uid, from_date.strftime('%d/%m/%Y'),
                                                                to_date.strftime('%d/%m/%Y'))


class OdmUtilsMethods(UtilsMethods):
    """ View containing outgoing mail utils methods """
    mainfile_type = 'dmsommainfile'

    def get_om_folder(self):
        """ Get the outgoing-mail folder """
        portal = getSite()
        return portal['outgoing-mail']

    def can_do_transition(self, transition):
        """ Used in guard expression for n_plus_1 transitions """
        if self.context.treating_groups is None:
            # print "no tg: False"
            return False
        way_index = transition.startswith('back_to') and 1 or 0
        # show only the next valid level
        state = api.content.get_state(self.context)
        transitions_levels = get_dms_config(['transitions_levels', 'dmsoutgoingmail'])
        if (self.context.treating_groups in transitions_levels[state] and
           transitions_levels[state][self.context.treating_groups][way_index] == transition):
            # print "from state: True"
            return True
        return False

    def scanned_col_cond(self):
        """ Condition for searchfor_scanned collection """
        return self.is_in_user_groups(['encodeurs', 'expedition'], admin=False, suffixes=[CREATING_GROUP_SUFFIX])

    def is_odt_activated(self):
        registry = getUtility(IRegistry)
        return registry['imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_odt_mainfile']


class TaskUtilsMethods(UtilsMethods):
    """ View containing task utils methods """

    def can_do_transition(self, transition):
        """
            Check if assigned_user is set or if the test is required or if the user is admin.
            Used in guard expression for propose_to_agent transition
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


class Dummy(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


def update_solr_config():
    """ Update config following buildout var """
    full_key = 'collective.solr.port'
    configured_port = api.portal.get_registry_record(full_key, default=None)
    if configured_port is None:
        return
    new_port = int(os.getenv('SOLR_PORT', ''))
    if new_port and new_port != configured_port:
        api.portal.set_registry_record(full_key, new_port)
