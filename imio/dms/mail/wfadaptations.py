# -*- coding: utf-8 -*-

from collections import OrderedDict
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import set_registry_functions
from collective.wfadaptations.api import get_applied_adaptations
from collective.wfadaptations.wfadaptation import WorkflowAdaptationBase
from imio.dms.mail import _tr as _
from imio.dms.mail import AUC_RECORD
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import set_dms_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import update_transitions_levels_config
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.pyutils.utils import insert_in_ordereddict
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from zope import schema
from zope.component import getUtility
from zope.interface import Interface
from zope.interface import provider
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


"""
  incomingmail_workflow adaptation
"""


class IIMPreValidationParameters(Interface):

    state_title = schema.TextLine(
        title=u'State title',
        default=u'À valider avant le DG',
        required=True)

    forward_transition_title = schema.TextLine(
        title=u'Forward transition title',
        default=u'Proposer pour prévalidation DG',
        required=True)

    backward_transition_title = schema.TextLine(
        title=u'Backward transition title',
        default=u'Renvoyer pour prévalidation DG',
        required=True)


class IMPreManagerValidation(WorkflowAdaptationBase):

    schema = IIMPreValidationParameters

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'incomingmail_workflow':
            return False, _("This workflow adaptation is only valid for ${workflow} !",
                            mapping={'workflow': 'incomingmail_workflow'})
        portal = api.portal.get()
        wtool = portal.portal_workflow
        wf = wtool['incomingmail_workflow']
        new_state_id = 'proposed_to_pre_manager'
        msg = self.check_state_in_workflow(wf, new_state_id)
        if not msg:
            return False, 'State %s already in workflow' % new_state_id
        wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'])
        next_states = [st for (st, tr) in wf_from_to['to']]

        # add state
        wf.states.addState(new_state_id)
        state = wf.states[new_state_id]
        state.setProperties(
            title=parameters['state_title'].encode('utf8'), description='',
            transitions=['back_to_creation', 'propose_to_manager'])
        # permissions
        perms = {
            'Access contents information': ('Editor', 'Manager', 'Owner', 'Reader', 'Reviewer', 'Site Administrator'),
            'Add portal content': ('Contributor', 'Manager', 'Site Administrator'),
            'Delete objects': ('Manager', 'Site Administrator'),
            'Modify portal content': ('Editor', 'Manager', 'Site Administrator'),
            'Review portal content': ('Manager', 'Reviewer', 'Site Administrator'),
            'View': ('Editor', 'Manager', 'Owner', 'Reader', 'Reviewer', 'Site Administrator'),
            'collective.dms.basecontent: Add DmsFile': ('DmsFile Contributor', 'Manager', 'Site Administrator'),
            'imio.dms.mail: Write mail base fields': ('Manager', 'Site Administrator', 'Base Field Writer'),
            'imio.dms.mail: Write treating group field': ('Manager', 'Site Administrator', 'Treating Group Writer'),
        }
        state.permission_roles = perms

        # add transitions
        propose_tr_id = 'propose_to_pre_manager'
        wf.transitions.addTransition(propose_tr_id)
        wf.transitions[propose_tr_id].setProperties(
            title=parameters['forward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=propose_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_propose_to_pre_manager.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})
        back_tr_id = 'back_to_pre_manager'
        wf.transitions.addTransition(back_tr_id)
        wf.transitions[back_tr_id].setProperties(
            title=parameters['backward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=back_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_back_to_pre_manager.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})

        # Other state transitions
        transitions = list(wf.states['proposed_to_manager'].transitions)
        transitions.append(back_tr_id)
        wf.states['proposed_to_manager'].transitions = tuple(transitions)
        transitions = list(wf.states['created'].transitions)
        transitions.append(propose_tr_id)
        wf.states['created'].transitions = tuple(transitions)

        # pre_manager group
        if api.group.get('pre_manager') is None:
            api.group.create('pre_manager', '1 prévalidation DG')
            # portal['outgoing-mail'].manage_addLocalRoles('pre_manager', ['Contributor'])
            portal['contacts'].manage_addLocalRoles('pre_manager', ['Contributor', 'Editor', 'Reader'])
            portal['contacts']['contact-lists-folder'].manage_addLocalRoles('pre_manager',
                                                                            ['Contributor', 'Editor', 'Reader'])

        # ajouter config local roles
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        lrsc = lr['static_config']
        if new_state_id not in lrsc:
            lrsc[new_state_id] = {'pre_manager': {'roles': ['Editor', 'Reviewer']},
                                  'encodeurs': {'roles': ['Reader']},
                                  'dir_general': {'roles': ['Reader']}}
            lrsc['proposed_to_manager'].update({'pre_manager': {'roles': ['Reader']}})
            for st in next_states:
                lrsc[st].update({'pre_manager': {'roles': ['Reader']}})
            lrsc['in_treatment'].update({'pre_manager': {'roles': ['Reader']}})
            lrsc['closed'].update({'pre_manager': {'roles': ['Reader']}})
        # We need to indicate that the object has been modified and must be 'saved'
        lr._p_changed = True

        # add collection
        folder = portal['incoming-mail']['mail-searches']
        col_id = 'searchfor_proposed_to_pre_manager'
        col_title = u'État: {}'.format(parameters['state_title'])
        if col_id not in folder:
            next_col = folder['searchfor_{}'.format(next_states[-1])]
            folder.invokeFactory('DashboardCollection', id=col_id, title=col_title, enabled=True,
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['dmsincomingmail', 'dmsincoming_email']},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [new_state_id]}],
                                 customViewFields=tuple(next_col.customViewFields),
                                 tal_condition="python: object.restrictedTraverse('idm-utils')."
                                               "proposed_to_pre_manager_col_cond()",
                                 showNumberOfItems=False,
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'organization_type', sort_reversed=True, b_size=30, limit=0)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.moveObjectToPosition(col_id, folder.getObjectPosition('searchfor_proposed_to_manager'))

        # update configuration annotation
        config = get_dms_config(['review_levels', 'dmsincomingmail'])
        if 'pre_manager' not in config:
            new_value = OrderedDict([('pre_manager', {'st': [new_state_id]})] + config.items())
            set_dms_config(keys=['review_levels', 'dmsincomingmail'], value=new_value)
        config = get_dms_config(['review_states', 'dmsincomingmail'])
        if new_state_id not in config:
            new_value = OrderedDict([(new_state_id, {'group': 'pre_manager'})] + config.items())
            set_dms_config(keys=['review_states', 'dmsincomingmail'], value=new_value)

        # update state list
        invalidate_cachekey_volatile_for('collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsincomingmail')

        # update actionspanel back transitions registry
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        if 'dmsincomingmail.back_to_pre_manager|' not in lst:
            lst.append('dmsincomingmail.back_to_pre_manager|')
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           lst)

        return True, ''


@provider(IContextSourceBinder)
def im_service_validation_levels(context):
    # must return next possible level only
    config = get_dms_config(['review_levels', 'dmsincomingmail'])
    for i in range(1, 6):  # 5 validation levels
        if '_n_plus_{}'.format(i) not in config:
            break
    else:
        return SimpleVocabulary([])
    return SimpleVocabulary([SimpleTerm(value=i)])


class IIMServiceValidationParameters(Interface):

    validation_level = schema.Choice(
        title=u'Service validation level',
        required=True,
        source=im_service_validation_levels,
    )

    state_title = schema.TextLine(
        title=u'State title',
        default=u'À valider par ',
        required=True,
    )

    forward_transition_title = schema.TextLine(
        title=u'Title of forward transition',
        default=u'Proposer ',
        required=True,
    )

    backward_transition_title = schema.TextLine(
        title=u'Title of backward transition',
        default=u'Renvoyer ',
        required=True,
    )

    function_title = schema.TextLine(
        title=u'Title of plonegroup function',
        default=u'N+',
        required=True,
    )


class IMServiceValidation(WorkflowAdaptationBase):

    schema = IIMServiceValidationParameters
    multiplicity = True

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'incomingmail_workflow':
            return False, _("This workflow adaptation is only valid for ${workflow} !",
                            mapping={'workflow': 'incomingmail_workflow'})
        portal = api.portal.get()
        wtool = portal.portal_workflow
        level = parameters['validation_level']
        wf = wtool['incomingmail_workflow']
        new_id = 'n_plus_{}'.format(level)
        new_state_id = 'proposed_to_{}'.format(new_id)
        wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'])
        transitions = [tr for (st, tr) in wf_from_to['from']]  # back transitions for new state
        transitions += [tr for (st, tr) in wf_from_to['to']]  # agent + previous levels
        next_states = [st for (st, tr) in wf_from_to['to']]

        # store current level in dms_config
        propose_tr_id = 'propose_to_{}'.format(new_id)
        wf_from_to['to'] += [(new_state_id, propose_tr_id)]
        set_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'], wf_from_to)

        # add state
        msg = self.check_state_in_workflow(wf, new_state_id)
        if not msg:
            return False, 'State {} already in workflow'.format(new_state_id)
        wf.states.addState(new_state_id)
        state = wf.states[new_state_id]
        state.setProperties(
            title=parameters['state_title'].encode('utf8'), description='',
            transitions=transitions)
        # permissions
        perms = {
            'Access contents information': ('Editor', 'Manager', 'Reader', 'Reviewer', 'Site Administrator'),
            'Add portal content': ('Contributor', 'Manager', 'Site Administrator'),
            'Delete objects': ('Manager', 'Site Administrator'),
            'Modify portal content': ('Editor', 'Manager', 'Site Administrator'),
            'Review portal content': ('Manager', 'Reviewer', 'Site Administrator'),
            'View': ('Editor', 'Manager', 'Reader', 'Reviewer', 'Site Administrator'),
            'collective.dms.basecontent: Add DmsFile': ('DmsFile Contributor', 'Manager', 'Site Administrator'),
            'imio.dms.mail: Write mail base fields': ('Manager', 'Site Administrator', 'Base Field Writer'),
            'imio.dms.mail: Write treating group field': ('Manager', 'Site Administrator', 'Treating Group Writer'),
        }
        state.permission_roles = perms

        # add transitions
        wf.transitions.addTransition(propose_tr_id)
        wf.transitions[propose_tr_id].setProperties(
            title=parameters['forward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=propose_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_propose_to_n_plus.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content',
                   'guard_expr': "python:object.restrictedTraverse('idm-utils')."
                                 "can_do_transition('{}')".format(propose_tr_id)})
        back_tr_id = 'back_to_{}'.format(new_id)
        wf.transitions.addTransition(back_tr_id)
        wf.transitions[back_tr_id].setProperties(
            title=parameters['backward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=back_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_back_to_n_plus.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content',
                   'guard_expr': "python:object.restrictedTraverse('idm-utils')."
                                 "can_do_transition('{}')".format(back_tr_id)})

        # modify existing states
        # add new back_to transition on next states
        for next_state_id in next_states:
            next_state = wf.states[next_state_id]
            transitions = list(next_state.transitions)
            transitions.append(back_tr_id)
            next_state.transitions = tuple(transitions)

        # add new propose_to transition on previous states
        for st in [st for (st, tr) in wf_from_to['from']]:
            previous_state = wf.states[st]
            transitions = list(previous_state.transitions)
            transitions.append(propose_tr_id)
            previous_state.transitions = tuple(transitions)

        # add function
        functions = get_registry_functions()
        if new_id not in [fct['fct_id'] for fct in functions]:
            functions.append({'fct_title': parameters['function_title'], 'fct_id': unicode(new_id), 'fct_orgs': [],
                              'fct_management': True, 'enabled': True})
            set_registry_functions(functions)

        # add local roles config
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        lrs = lr['static_config']
        if new_state_id not in lrs:
            lrs[new_state_id] = {'dir_general': {'roles': ['Contributor', 'Editor', 'Reviewer',
                                                           'Base Field Writer', 'Treating Group Writer']},
                                 'encodeurs': {'roles': ['Reader']},
                                 'lecteurs_globaux_ce': {'roles': ['Reader']}}
        lrt = lr['treating_groups']
        if 'creating_group' in lr:
            api.portal.show_message(_('Please update manually ${type} local roles for creating_group !',
                                      mapping={'type': 'dmsincomingmail'}), portal.REQUEST, type='warning')
        if new_state_id not in lrt:
            lrt[new_state_id] = {new_id: {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']}}
            for st in next_states:
                lrt[st].update({new_id: {'roles': ['Contributor', 'Editor', 'Reviewer']}})
            lrt['in_treatment'].update({new_id: {'roles': ['Contributor', 'Editor', 'Reviewer']}})
            lrt['closed'].update({new_id: {'roles': ['Reviewer']}})
        lrr = lr['recipient_groups']
        if new_state_id not in lrr:
            lrr[new_state_id] = {new_id: {'roles': ['Reader']}}
            for st in next_states:
                lrr[st].update({new_id: {'roles': ['Reader']}})
            lrr['in_treatment'].update({new_id: {'roles': ['Reader']}})
            lrr['closed'].update({new_id: {'roles': ['Reader']}})
        # We need to indicate that the object has been modified and must be 'saved'
        lr._p_changed = True

        # add collection
        folder = portal['incoming-mail']['mail-searches']
        col_id = 'searchfor_{}'.format(new_state_id)
        col_title = u'État: {}'.format(parameters['state_title'])
        if col_id not in folder:
            next_col = folder['searchfor_{}'.format(next_states[-1])]
            folder.invokeFactory('DashboardCollection', id=col_id, title=col_title, enabled=True,
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['dmsincomingmail', 'dmsincoming_email']},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [new_state_id]}],
                                 customViewFields=tuple(next_col.customViewFields),
                                 tal_condition="python: object.restrictedTraverse('idm-utils')."
                                               "proposed_to_n_plus_col_cond()",
                                 showNumberOfItems=False,
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'organization_type', sort_reversed=True, b_size=30, limit=0)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.moveObjectToPosition(col_id, folder.getObjectPosition('searchfor_{}'.format(next_states[-1])))

        # update showNumberOfItems on 'to_treat_in_my_group'
        auc = api.portal.get_registry_record(AUC_RECORD)
        snoi = False
        if auc == u'no_check':
            snoi = True
        if folder['to_treat_in_my_group'].showNumberOfItems != snoi:
            folder['to_treat_in_my_group'].showNumberOfItems = snoi  # noqa
            folder['to_treat_in_my_group'].reindexObject()

        # update configuration annotation
        config = get_dms_config(['review_levels', 'dmsincomingmail'])
        suffix = '_{}'.format(new_id)
        if suffix not in config:
            value = (suffix, {'st': [new_state_id], 'org': 'treating_groups'})
            new_config = insert_in_ordereddict(config, value, after_key='dir_general', at_position=0)
            set_dms_config(keys=['review_levels', 'dmsincomingmail'], value=new_config)
        config = get_dms_config(['review_states', 'dmsincomingmail'])
        if new_state_id not in config:
            value = (new_state_id, {'group': suffix, 'org': 'treating_groups'})
            new_config = insert_in_ordereddict(config, value, after_key='proposed_to_manager', at_position=0)
            set_dms_config(keys=['review_states', 'dmsincomingmail'], value=new_config)
        # update dms config
        update_transitions_auc_config('dmsincomingmail')
        update_transitions_levels_config(['dmsincomingmail'])

        # update cache
        invalidate_cachekey_volatile_for('collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsincomingmail')

        # update actionspanel back transitions registry
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        if 'dmsincomingmail.{}|'.format(back_tr_id) not in lst:
            lst.append('dmsincomingmail.{}|'.format(back_tr_id))
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           lst)
        # update remark states
        lst = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states')
        if new_state_id not in lst:
            lst.insert(0, new_state_id)
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_remark_states',
                                           lst)
        # TODO reindex all im and files
        return True, ''


class IOMServiceValidationParameters(IIMServiceValidationParameters):

    validation_level = schema.Choice(
        title=u'Service validation level',
        required=True,
        vocabulary=SimpleVocabulary([SimpleTerm(value=1)]),
    )


"""
    outgoingmail_workflow adaptation
"""


class OMServiceValidation(WorkflowAdaptationBase):

    schema = IOMServiceValidationParameters
    multiplicity = False

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'outgoingmail_workflow':
            return False, _("This workflow adaptation is only valid for ${workflow} !",
                            mapping={'workflow': 'outgoingmail_workflow'})
        portal = api.portal.get()
        wtool = portal.portal_workflow
        level = parameters['validation_level']
        wf = wtool['outgoingmail_workflow']
        new_id = 'n_plus_{}'.format(level)
        new_state_id = 'proposed_to_{}'.format(new_id)
        wf_from_to = get_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus'])
        # from: ('created', 'back_to_creation')
        # to: ('to_be_signed', 'propose_to_be_signed'), ('to_print', 'set_to_print')
        transitions = [tr for (st, tr) in wf_from_to['from']] + [tr for (st, tr) in wf_from_to['to']]
        to_states = [st for (st, tr) in wf_from_to['to']]
        # store current level in dms_config
        propose_tr_id = 'propose_to_{}'.format(new_id)
        # wf_from_to['to'].append((new_state_id, propose_tr_id))
        # set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus'], wf_from_to)

        # add state
        msg = self.check_state_in_workflow(wf, new_state_id)
        if not msg:
            return False, 'State {} already in workflow'.format(new_state_id)
        wf.states.addState(new_state_id)
        state = wf.states[new_state_id]
        state.setProperties(
            title=parameters['state_title'].encode('utf8'), description='',
            transitions=transitions)
        # permissions
        perms = {
            'Access contents information': ('Editor', 'Manager', 'Owner', 'Reader', 'Reviewer', 'Site Administrator'),
            'Add portal content': ('Contributor', 'Manager', 'Site Administrator'),
            'Delete objects': ('Manager', 'Site Administrator'),
            'Modify portal content': ('Editor', 'Manager', 'Site Administrator'),
            'Review portal content': ('Manager', 'Reviewer', 'Site Administrator'),
            'View': ('Editor', 'Manager', 'Owner', 'Reader', 'Reviewer', 'Site Administrator'),
            'collective.dms.basecontent: Add DmsFile': ('DmsFile Contributor', 'Manager', 'Site Administrator'),
            'imio.dms.mail: Write mail base fields': ('Manager', 'Site Administrator', 'Base Field Writer'),
            'imio.dms.mail: Write treating group field': ('Manager', 'Site Administrator', 'Treating Group Writer'),
        }
        state.permission_roles = perms

        # add transitions
        wf.transitions.addTransition(propose_tr_id)
        wf.transitions[propose_tr_id].setProperties(
            title=parameters['forward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=propose_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/om_propose_to_n_plus.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content',
                   'guard_expr': "python:object.restrictedTraverse('odm-utils')."
                                 "can_do_transition('{}')".format(propose_tr_id)})
        back_tr_id = 'back_to_{}'.format(new_id)
        wf.transitions.addTransition(back_tr_id)
        wf.transitions[back_tr_id].setProperties(
            title=parameters['backward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=back_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/om_back_to_n_plus.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content',
                   'guard_expr': "python:object.restrictedTraverse('odm-utils')."
                                 "can_do_transition('{}')".format(back_tr_id)})

        # modify existing states
        # add new back_to transition on next states
        for next_state_id in to_states:
            next_state = wf.states[next_state_id]
            transitions = list(next_state.transitions)
            transitions.append(back_tr_id)
            next_state.transitions = tuple(transitions)

        # add new propose_to transition on previous states
        for st in [st for (st, tr) in wf_from_to['from']]:
            previous_state = wf.states[st]
            transitions = list(previous_state.transitions)
            transitions.append(propose_tr_id)
            previous_state.transitions = tuple(transitions)

        # add function
        functions = get_registry_functions()
        if new_id not in [fct['fct_id'] for fct in functions]:
            functions.append({'fct_title': parameters['function_title'], 'fct_id': unicode(new_id), 'fct_orgs': [],
                              'fct_management': True, 'enabled': True})
            set_registry_functions(functions)

        # add local roles config
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        if 'creating_group' in lr:
            api.portal.show_message(_('Please update manually ${type} local roles for creating_group !',
                                      mapping={'type': 'dmsoutgoingmail'}), portal.REQUEST, type='warning')
        lrt = lr['treating_groups']
        if new_state_id not in lrt:
            lrt[new_state_id] = {new_id: {'roles': ['Contributor', 'Editor', 'Reviewer', 'DmsFile Contributor',
                                                    'Base Field Writer', 'Treating Group Writer']},
                                 'encodeur': {'roles': ['Reader']}}
            for st in to_states:
                lrt[st].update({new_id: {'roles': ['Reader']}})
            lrt['sent'].update({new_id: {'roles': ['Reader']}})
        lrr = lr['recipient_groups']
        if new_state_id not in lrr:
            lrr[new_state_id] = {new_id: {'roles': ['Reader']}}
            for st in to_states:
                lrr[st].update({new_id: {'roles': ['Reader']}})
            lrr['sent'].update({new_id: {'roles': ['Reader']}})
        # We need to indicate that the object has been modified and must be 'saved'
        lr._p_changed = True

        # add collection
        folder = portal['outgoing-mail']['mail-searches']
        col_id = 'searchfor_{}'.format(new_state_id)
        col_title = u'État: {}'.format(parameters['state_title'])
        if col_id not in folder:
            next_col = folder['searchfor_{}'.format(to_states[-1])]
            folder.invokeFactory('DashboardCollection', id=col_id, title=col_title, enabled=True,
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['dmsoutgoingmail', 'dmsoutgoing_email']},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [new_state_id]}],
                                 customViewFields=tuple(next_col.customViewFields),
                                 showNumberOfItems=False,
                                 sort_on=u'sortable_title', sort_reversed=True, b_size=30, limit=0)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.moveObjectToPosition(col_id, folder.getObjectPosition('searchfor_{}'.format(to_states[-1])))

        if not folder['to_validate'].enabled:
            folder['to_validate'].enabled = True
            folder['to_validate'].reindexObject()

        # update configuration annotation
        config = get_dms_config(['review_levels', 'dmsoutgoingmail'])
        suffix = '_{}'.format(new_id)
        if suffix not in config:
            value = (suffix, {'st': [new_state_id], 'org': 'treating_groups'})
            new_config = insert_in_ordereddict(config, value, at_position=0)
            set_dms_config(keys=['review_levels', 'dmsoutgoingmail'], value=new_config)
        config = get_dms_config(['review_states', 'dmsoutgoingmail'])
        if new_state_id not in config:
            value = (new_state_id, {'group': suffix, 'org': 'treating_groups'})
            new_config = insert_in_ordereddict(config, value, at_position=0)
            set_dms_config(keys=['review_states', 'dmsoutgoingmail'], value=new_config)
        # update dms config
        update_transitions_levels_config(['dmsoutgoingmail'])

        # update cache
        invalidate_cachekey_volatile_for('collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsoutgoingmail')

        # update actionspanel back transitions registry
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        if 'dmsoutgoingmail.{}|'.format(back_tr_id) not in lst:
            lst.append('dmsoutgoingmail.{}|'.format(back_tr_id))
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           lst)
        # update remark states
        lst = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states',
                                             default=False) or []
        if new_state_id not in lst:
            lst.insert(0, new_state_id)
            api.portal.set_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_remark_states',
                                           lst)

        col = folder['om_treating']
        query = list(col.query)
        modif = False
        for dic in query:
            if dic['i'] == 'review_state' and new_state_id not in dic['v']:
                modif = True
                if 'proposed_to_service_chief' in dic['v']:
                    dic['v'].remove('proposed_to_service_chief')
                dic['v'] += [new_state_id]
        if modif:
            col.query = query

        # TODO reindex all om and files
        return True, ''


class OMToPrintAdaptation(WorkflowAdaptationBase):

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'outgoingmail_workflow':
            return False, _("This workflow adaptation is only valid for ${workflow} !",
                            mapping={'workflow': 'outgoingmail_workflow'})
        portal = api.portal.get()
        wtool = portal.portal_workflow
        wf = wtool['outgoingmail_workflow']
        new_state_id = 'to_print'
        to_tr_id = 'set_to_print'
        back_tr_id = 'back_to_print'
        msg = self.check_state_in_workflow(wf, new_state_id)
        if not msg:
            return False, 'State to_print already in workflow'

        transitions = ['propose_to_be_signed', 'back_to_creation']
        has_n_plus_1 = False
        # is n+1 already applied ?
        applied_wfa = [dic['adaptation'] for dic in get_applied_adaptations()]
        if u'imio.dms.mail.wfadaptations.OMServiceValidation' in applied_wfa:
            transitions.append('back_to_n_plus_1')
            has_n_plus_1 = True

        # modify wf_from_to
        nplus_to = get_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'])
        nplus_to.insert(1, (new_state_id, to_tr_id))
        set_dms_config(['wf_from_to', 'dmsoutgoingmail', 'n_plus', 'to'], nplus_to)

        # add state
        wf.states.addState(new_state_id)
        state = wf.states[new_state_id]
        state.setProperties(
            title='om_to_print', description='',
            transitions=transitions)
        # permissions
        perms = {
            'Access contents information': ('Editor', 'Manager', 'Owner', 'Reader', 'Reviewer', 'Site Administrator'),
            'Add portal content': ('Contributor', 'Manager', 'Site Administrator'),
            'Delete objects': ('Manager', 'Site Administrator'),
            'Modify portal content': ('Editor', 'Manager', 'Site Administrator'),
            'Review portal content': ('Manager', 'Reviewer', 'Site Administrator'),
            'View': ('Editor', 'Manager', 'Owner', 'Reader', 'Reviewer', 'Site Administrator'),
            'collective.dms.basecontent: Add DmsFile': ('DmsFile Contributor', 'Manager', 'Site Administrator'),
            'imio.dms.mail: Write mail base fields': ('Manager', 'Site Administrator', 'Base Field Writer'),
            'imio.dms.mail: Write treating group field': ('Manager', 'Site Administrator', 'Treating Group Writer'),
        }
        state.permission_roles = perms

        # add transitions
        wf.transitions.addTransition(to_tr_id)
        wf.transitions[to_tr_id].setProperties(
            title='om_set_to_print',
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name='om_set_to_print', actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/om_set_to_print.png', actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})
        wf.transitions.addTransition(back_tr_id)
        wf.transitions[back_tr_id].setProperties(
            title='om_back_to_print',
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name='om_back_to_print', actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/om_back_to_print.png', actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})

        # proposed_to_n_plus_1 transitions
        if has_n_plus_1:
            transitions = list(wf.states['proposed_to_n_plus_1'].transitions)
            transitions.append(to_tr_id)
            wf.states['proposed_to_n_plus_1'].transitions = tuple(transitions)
        # created transitions
        transitions = list(wf.states['created'].transitions)
        transitions.append(to_tr_id)
        wf.states['created'].transitions = tuple(transitions)
        # to_be_signed transitions
        transitions = list(wf.states['to_be_signed'].transitions)
        transitions.append(back_tr_id)
        wf.states['to_be_signed'].transitions = tuple(transitions)

        # ajouter config local roles
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        lrsc = lr['static_config']
        if new_state_id not in lrsc:
            lrsc[new_state_id] = {'expedition': {'roles': ['Editor', 'Reviewer']},
                                  'encodeurs': {'roles': ['Reader']},
                                  'dir_general': {'roles': ['Reader']}}
        lrtg = lr['treating_groups']
        if new_state_id not in lrtg:
            dic = {'editeur': {'roles': ['Reader']},
                   'encodeur': {'roles': ['Reader', 'Reviewer']},
                   'lecteur': {'roles': ['Reader']}}
            if has_n_plus_1:
                dic.update({'n_plus_1': {'roles': ['Reader', 'Reviewer']}})
            lrtg[new_state_id] = dic
        lrrg = lr['recipient_groups']
        if new_state_id not in lrrg:
            dic = {'editeur': {'roles': ['Reader']},
                   'encodeur': {'roles': ['Reader']},
                   'lecteur': {'roles': ['Reader']}}
            if has_n_plus_1:
                dic.update({'n_plus_1': {'roles': ['Reader']}})
            lrrg[new_state_id] = dic
        # We need to indicate that the object has been modified and must be 'saved'
        lr._p_changed = True

        # add collection
        folder = portal['outgoing-mail']['mail-searches']
        col_id = 'searchfor_to_print'
        if col_id not in folder:
            next_col = folder['searchfor_to_be_signed']
            folder.invokeFactory('DashboardCollection', id=col_id, title=_(col_id),
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['dmsoutgoingmail', 'dmsoutgoing_email']},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [new_state_id]}],
                                 customViewFields=tuple(next_col.customViewFields),
                                 tal_condition=None,
                                 showNumberOfItems=True,
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'sortable_title', sort_reversed=True, b_size=30, limit=0, enabled=True)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.moveObjectToPosition(col_id, folder.getObjectPosition('searchfor_to_be_signed'))
            # Add template to folder
            tmpl = portal['templates']['om']['d-print']
            cols = tmpl.dashboard_collections
            if col.UID() not in cols:
                cols.append(col.UID())
                tmpl.dashboard_collections = cols

        col = folder['om_treating']
        query = list(col.query)
        modif = False
        for dic in query:
            if dic['i'] == 'review_state' and new_state_id not in dic['v']:
                modif = True
                dic['v'] += [new_state_id]
        if modif:
            col.query = query

        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsoutgoingmail')

        return True, ''


"""
  task_workflow adaptation
"""


class TaskServiceValidation(WorkflowAdaptationBase):
    """
        Update task_workflow:
        * modify new transition back_in_created2 and back_in_to_assign
    """

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'task_workflow':
            return False, _("This workflow adaptation is only valid for ${workflow} !",
                            mapping={'workflow': 'task_workflow'})
        portal = api.portal.get()
        wtool = portal.portal_workflow
        new_id = 'n_plus_1'
        function_title = u'N+1'
        wf = wtool['task_workflow']

        # add 'back_in_to_assign' on 'to_do' state
        state = wf.states['to_do']
        transitions = list(state.transitions)  # noqa
        if 'back_in_to_assign' not in transitions:
            transitions.append('back_in_to_assign')
            state.transitions = tuple(transitions)

        # add conditions to transitions
        for tr_id in ('back_in_to_assign', 'back_in_created2'):
            tr = wf.transitions[tr_id]
            guard = tr.getGuard()
            if guard.changeFromProperties({'guard_expr': "python:object.restrictedTraverse('task-utils')."
                                                         "can_do_transition('{}')".format(tr_id)}):
                tr.guard = guard

        # add function
        functions = get_registry_functions()
        if new_id not in [fct['fct_id'] for fct in functions]:
            functions.append({'fct_title': function_title, 'fct_id': unicode(new_id), 'fct_orgs': [],
                              'fct_management': True, 'enabled': True})
            set_registry_functions(functions)

        # add local roles config
        fti = getUtility(IDexterityFTI, name='task')
        lr = getattr(fti, 'localroles')
        lrag = lr['assigned_group']
        if new_id not in lrag['to_do']:
            for st in ['to_assign', 'to_do', 'in_progress', 'realized']:
                lrag[st].update({new_id: {'roles': ['Contributor', 'Editor', 'Reviewer'],
                                          'rel': "{'collective.task.related_taskcontainer':['Reader']}"}})
            lrag['closed'].update({new_id: {'roles': ['Editor', 'Reviewer'],
                                            'rel': "{'collective.task.related_taskcontainer':['Reader']}"}})
        lrpag = lr['parents_assigned_groups']
        if new_id not in lrpag['to_do']:
            for st in ['to_assign', 'to_do', 'in_progress', 'realized', 'closed']:
                lrpag[st].update({new_id: {'roles': ['Reader']}})
        lr._p_changed = True

        # update collections
        folder = portal['tasks']['task-searches']
        if folder['to_treat_in_my_group'].showNumberOfItems:
            folder['to_treat_in_my_group'].showNumberOfItems = False  # noqa
            folder['to_treat_in_my_group'].reindexObject()
        for cid in ('to_assign', 'to_close'):
            if not folder[cid].enabled:
                folder[cid].enabled = True
                folder[cid].reindexObject()

        # update configuration annotation
        config = get_dms_config(['review_levels', 'task'])
        suffix = '_{}'.format(new_id)
        if suffix not in config:
            value = (suffix, {'st': ['to_assign', 'realized'], 'org': 'assigned_group'})
            new_config = insert_in_ordereddict(config, value, at_position=0)
            set_dms_config(keys=['review_levels', 'task'], value=new_config)
        new_config = get_dms_config(['review_states', 'task'])
        if 'to_assign' not in config:
            for st in ('realized', 'to_assign'):
                value = (st, {'group': suffix, 'org': 'assigned_group'})
                new_config = insert_in_ordereddict(new_config, value, at_position=0)
            set_dms_config(keys=['review_states', 'task'], value=new_config)

        update_transitions_levels_config(['task'])

        # update cache
        invalidate_cachekey_volatile_for('collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')

        # TODO reindex all task and ?
        return True, ''
