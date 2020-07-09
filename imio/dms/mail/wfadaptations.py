# -*- coding: utf-8 -*-

from collections import OrderedDict
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import set_registry_functions
from collective.wfadaptations.wfadaptation import WorkflowAdaptationBase
from imio.dms.mail import _tr as _
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import set_dms_config
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.pyutils.utils import insert_in_ordereddict
from plone import api
from plone.dexterity.interfaces import IDexterityFTI
from zope import schema
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import Interface
from zope.interface import provider
from zope.schema.interfaces import IContextAwareDefaultFactory
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class IEmergencyZoneParameters(Interface):

    manager_suffix = schema.TextLine(
        title=u'Manager suffix',
        default=u'_zs',
        required=True)


class EmergencyZoneAdaptation(WorkflowAdaptationBase):

    schema = IEmergencyZoneParameters

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'incomingmail_workflow':
            return False, _("incomingmail_workflow is not selected")
        portal = api.portal.get()
        wtool = portal.portal_workflow
        # change state title.
        im_workflow = wtool['incomingmail_workflow']
        msg = self.check_state_in_workflow(im_workflow, 'proposed_to_manager')
        if msg:
            return False, msg
        state = im_workflow.states['proposed_to_manager']
        new_title = 'proposed_to_manager%s' % parameters['manager_suffix']
        if state.title != new_title:
            state.title = str(new_title)

        # change transition title.
        for tr in ('back_to_manager', 'propose_to_manager'):
            msg = self.check_transition_in_workflow(im_workflow, tr)
            if msg:
                return False, msg
            transition = im_workflow.transitions[tr]
            new_title = '%s%s' % (tr, parameters['manager_suffix'])
            if transition.title != new_title:
                transition.title = str(new_title)

        # change collection title
        collection = portal.restrictedTraverse('incoming-mail/mail-searches/searchfor_proposed_to_manager',
                                               default=None)
        if not collection:
            return False, "'incoming-mail/mail-searches/searchfor_proposed_to_manager' not found"
        if collection.Title().endswith(' DG'):
            collection.setTitle(collection.Title().replace(' DG', ' CZ'))
            collection.reindexObject(['Title', 'SearchableText', 'sortable_title'])
        return True, ''


class OMToPrintAdaptation(WorkflowAdaptationBase):

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'outgoingmail_workflow':
            return False, _("outgoingmail_workflow is not selected")
        portal = api.portal.get()
        wtool = portal.portal_workflow
        # change state title.
        wf = wtool['outgoingmail_workflow']
        msg = self.check_state_in_workflow(wf, 'to_print')
        if not msg:
            return False, 'State to_print already in workflow'

        # add state
        wf.states.addState('to_print')
        to_print = wf.states['to_print']

        # add transitions
        wf.transitions.addTransition('set_to_print')
        wf.transitions['set_to_print'].setProperties(
            title='om_set_to_print',
            new_state_id='to_print', trigger_type=1, script_name='',
            actbox_name='om_set_to_print', actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/om_set_to_print.png', actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})
        wf.transitions.addTransition('back_to_print')
        wf.transitions['back_to_print'].setProperties(
            title='om_back_to_print',
            new_state_id='to_print', trigger_type=1, script_name='',
            actbox_name='om_back_to_print', actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/om_back_to_print.png', actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})

        # configure states
        to_print.setProperties(
            title='om_to_print', description='',
            transitions=['back_to_service_chief', 'propose_to_be_signed', 'back_to_creation'])
        # proposed_to_service_chief transitions
        transitions = list(wf.states['proposed_to_service_chief'].transitions)
        transitions.append('set_to_print')
        wf.states['proposed_to_service_chief'].transitions = tuple(transitions)
        # created transitions
        transitions = list(wf.states['created'].transitions)
        transitions.append('set_to_print')
        wf.states['created'].transitions = tuple(transitions)
        # to_be_signed transitions
        transitions = list(wf.states['to_be_signed'].transitions)
        transitions.append('back_to_print')
        wf.states['to_be_signed'].transitions = tuple(transitions)

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
        to_print.permission_roles = perms
        # proposed.setPermission(permission, 0, roles)

        # ajouter config local roles
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        lrsc = lr['static_config']
        if 'to_print' not in lrsc:
            lrsc['to_print'] = {'expedition': {'roles': ['Editor', 'Reviewer']},
                                'encodeurs': {'roles': ['Reader']},
                                'dir_general': {'roles': ['Reader']}}
        lrtg = lr['treating_groups']
        if 'to_print' not in lrtg:
            lrtg['to_print'] = {'validateur': {'roles': ['Reader', 'Reviewer']},
                                'editeur': {'roles': ['Reader']},
                                'encodeur': {'roles': ['Reader', 'Reviewer']},
                                'lecteur': {'roles': ['Reader']}}
        lrrg = lr['recipient_groups']
        if 'to_print' not in lrrg:
            lrrg['to_print'] = {'validateur': {'roles': ['Reader']},
                                'editeur': {'roles': ['Reader']},
                                'encodeur': {'roles': ['Reader']},
                                'lecteur': {'roles': ['Reader']}}
        # We need to indicate that the object has been modified and must be 'saved'
        lr._p_changed = True

        # add collection
        folder = portal['outgoing-mail']['mail-searches']
        col_id = 'searchfor_to_print'
        if col_id not in folder:
            folder.invokeFactory('DashboardCollection', id=col_id, title=_(col_id),
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['dmsoutgoingmail']},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['to_print']}],
                                 customViewFields=(u'select_row', u'pretty_link', u'treating_groups', u'sender',
                                                   u'recipients', u'mail_type', u'assigned_user', u'CreationDate',
                                                   u'actions'),
                                 tal_condition=None,
                                 showNumberOfItems=True,
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'created', sort_reversed=True, b_size=30, limit=0, enabled=True)
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
        col.query = [
            {'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is', 'v': ['dmsoutgoingmail']},
            {'i': 'assigned_user', 'o': 'plone.app.querystring.operation.string.currentUser'},
            {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is', 'v':
                ['proposed_to_service_chief', 'to_print', 'to_be_signed']}]

        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsoutgoingmail')

        return True, ''


@provider(IContextAwareDefaultFactory)
def impv_state_default(context):
    return translate(u'proposed_to_pre_manager', domain='plone', context=context.REQUEST)


@provider(IContextAwareDefaultFactory)
def impv_fw_tr_default(context):
    return translate(u'propose_to_pre_manager', domain='plone', context=context.REQUEST)


@provider(IContextAwareDefaultFactory)
def impv_bw_tr_default(context):
    return translate(u'back_to_pre_manager', domain='plone', context=context.REQUEST)


@provider(IContextAwareDefaultFactory)
def impv_collection_default(context):
    return translate(u'searchfor_proposed_to_pre_manager', domain='imio.dms.mail', context=context.REQUEST)


class IIMPreValidationParameters(Interface):

    state_title = schema.TextLine(
        title=u'State title',
        defaultFactory=impv_state_default,
        required=True)

    forward_transition_title = schema.TextLine(
        title=u'Forward transition title',
        defaultFactory=impv_fw_tr_default,
        required=True)

    backward_transition_title = schema.TextLine(
        title=u'Backward transition title',
        defaultFactory=impv_bw_tr_default,
        required=True)

    collection_title = schema.TextLine(
        title=u'Collection title',
        defaultFactory=impv_collection_default,
        required=True)


class IMPreManagerValidation(WorkflowAdaptationBase):

    schema = IIMPreValidationParameters

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'incomingmail_workflow':
            return False, _("incomingmail_workflow is not selected")
        portal = api.portal.get()
        wtool = portal.portal_workflow
        wf = wtool['incomingmail_workflow']
        msg = self.check_state_in_workflow(wf, 'proposed_to_pre_manager')
        if not msg:
            return False, 'State %s already in workflow' % 'proposed_to_pre_manager'

        # add state
        wf.states.addState('proposed_to_pre_manager')
        state = wf.states['proposed_to_pre_manager']
        state.setProperties(
            title=parameters['state_title'].encode('utf8'), description='',
            transitions=['back_to_creation', 'propose_to_manager'])

        # add transitions
        wf.transitions.addTransition('propose_to_pre_manager')
        wf.transitions['propose_to_pre_manager'].setProperties(
            title=parameters['forward_transition_title'].encode('utf8'),
            new_state_id='proposed_to_pre_manager', trigger_type=1, script_name='',
            actbox_name='propose_to_pre_manager', actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_propose_to_pre_manager.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})
        wf.transitions.addTransition('back_to_pre_manager')
        wf.transitions['back_to_pre_manager'].setProperties(
            title=parameters['backward_transition_title'].encode('utf8'),
            new_state_id='proposed_to_pre_manager', trigger_type=1, script_name='',
            actbox_name='back_to_pre_manager', actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_back_to_pre_manager.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})

        # Other state transitions
        transitions = list(wf.states['proposed_to_manager'].transitions)
        transitions.append('back_to_pre_manager')
        wf.states['proposed_to_manager'].transitions = tuple(transitions)
        transitions = list(wf.states['created'].transitions)
        transitions.append('propose_to_pre_manager')
        wf.states['created'].transitions = tuple(transitions)

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
        # proposed.setPermission(permission, 0, roles)

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
        if 'proposed_to_pre_manager' not in lrsc:
            lrsc['proposed_to_pre_manager'] = {'pre_manager': {'roles': ['Editor', 'Reviewer']},
                                               'encodeurs': {'roles': ['Reader']},
                                               'dir_general': {'roles': ['Reader']}}
            lrsc['proposed_to_manager'].update({'pre_manager': {'roles': ['Reader']}})
            lrsc['proposed_to_service_chief'].update({'pre_manager': {'roles': ['Reader']}})
            lrsc['proposed_to_agent'].update({'pre_manager': {'roles': ['Reader']}})
            lrsc['in_treatment'].update({'pre_manager': {'roles': ['Reader']}})
            lrsc['closed'].update({'pre_manager': {'roles': ['Reader']}})
        # We need to indicate that the object has been modified and must be 'saved'
        lr._p_changed = True

        # add collection
        folder = portal['incoming-mail']['mail-searches']
        col_id = 'searchfor_proposed_to_pre_manager'
        if col_id not in folder:
            folder.invokeFactory('DashboardCollection', id=col_id, title=parameters['collection_title'], enabled=True,
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['dmsincomingmail']},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['proposed_to_pre_manager']}],
                                 customViewFields=(u'select_row', u'pretty_link', u'treating_groups', u'assigned_user',
                                                   u'due_date', u'mail_type', u'sender', u'reception_date', u'actions'),
                                 tal_condition="python: object.restrictedTraverse('idm-utils')."
                                               "proposed_to_pre_manager_col_cond()",
                                 showNumberOfItems=False,
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'created', sort_reversed=True, b_size=30, limit=0)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.moveObjectToPosition(col_id, folder.getObjectPosition('searchfor_proposed_to_manager'))

        # update configuration annotation
        config = get_dms_config(['review_levels', 'dmsincomingmail'])
        if 'pre_manager' not in config:
            new_value = OrderedDict([('pre_manager', {'st': ['proposed_to_pre_manager']})] + config.items())
            set_dms_config(keys=['review_levels', 'dmsincomingmail'], value=new_value)
        config = get_dms_config(['review_states', 'dmsincomingmail'])
        if 'proposed_to_pre_manager' not in config:
            new_value = OrderedDict([('proposed_to_pre_manager', {'group': 'pre_manager'})] + config.items())
            set_dms_config(keys=['review_states', 'dmsincomingmail'], value=new_value)

        # update state list
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsincomingmail')

        # update actionspanel back transitions registry
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        if 'dmsincomingmail.back_to_pre_manager|' not in lst:
            lst.append('dmsincomingmail.back_to_pre_manager|')
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           lst)

        return True, ''


class IIMSkipProposeToServiceChiefParameters(Interface):

    assigned_user_check = schema.Bool(
        title=u'Assigned user check',
        description=u'Check if there is an assigned user before proposing incoming mail to an agent.',
        default=True
    )


class IMSkipProposeToServiceChief(WorkflowAdaptationBase):

    schema = IIMSkipProposeToServiceChiefParameters

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'incomingmail_workflow':
            return False, _("incomingmail_workflow is not selected")
        portal = api.portal.get()
        wtool = portal.portal_workflow
        im_workflow = wtool['incomingmail_workflow']
        msg = self.check_state_in_workflow(im_workflow, 'proposed_to_service_chief')
        if msg:
            return False, msg

        # remove state
        list_states = ['proposed_to_service_chief']
        im_workflow.states.deleteStates(list_states)

        # change created transition
        transitions = list(im_workflow.states['created'].transitions)
        transitions.remove('propose_to_service_chief')
        transitions.append('propose_to_agent')
        im_workflow.states['created'].transitions = tuple(transitions)
        # change proposed_to_manager transition
        transitions = list(im_workflow.states['proposed_to_manager'].transitions)
        transitions.remove('propose_to_service_chief')
        transitions.append('propose_to_agent')
        im_workflow.states['proposed_to_manager'].transitions = tuple(transitions)
        # change proposed_to_agent transition
        transitions = list(im_workflow.states['proposed_to_agent'].transitions)
        transitions.remove('back_to_service_chief')
        transitions.append('back_to_manager')
        transitions.append('back_to_creation')
        im_workflow.states['proposed_to_agent'].transitions = tuple(transitions)
        # remove transitions
        list_transitions = ['propose_to_service_chief', 'back_to_service_chief']
        im_workflow.transitions.deleteTransitions(list_transitions)

        # change assigned user verification option
        if not parameters['assigned_user_check']:
            api.portal.set_registry_record('assigned_user_check', False, IImioDmsMailConfig)
            # change transition titles
            for tr, title in (('back_to_agent', 'back_to_service'), ('propose_to_agent', 'propose_to_service')):
                msg = self.check_transition_in_workflow(im_workflow, tr)
                if msg:
                    return False, msg
                im_workflow.transitions[tr].title = str(title)

        # remove local roles
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        changed_flag = False
        for lrgroup in lr:
            if 'proposed_to_service_chief' in lr[lrgroup]:
                del lr[lrgroup]['proposed_to_service_chief']
                changed_flag = True
        if changed_flag:
            # the object has been modified and must be saved in db
            lr._p_changed = True

        # disable collection
        folder = portal['incoming-mail']['mail-searches']
        if folder['searchfor_proposed_to_service_chief'].enabled:
            folder['searchfor_proposed_to_service_chief'].enabled = False
            folder['searchfor_proposed_to_service_chief'].reindexObject()
            # update search collection list
            invalidate_cachekey_volatile_for('collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')

        # enable shoNumberOfItems on 'to_treat_in_my_group'
        if not folder['to_treat_in_my_group'].showNumberOfItems and not parameters['assigned_user_check']:
            folder['to_treat_in_my_group'].showNumberOfItems = True
            folder['to_treat_in_my_group'].reindexObject()

        # update state list
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsincomingmail')

        return True, ''


class OMSkipProposeToServiceChief(WorkflowAdaptationBase):

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'outgoingmail_workflow':
            return False, _("outgoingmail_workflow is not selected")
        portal = api.portal.get()
        wtool = portal.portal_workflow
        om_workflow = wtool['outgoingmail_workflow']
        msg = self.check_state_in_workflow(om_workflow, 'proposed_to_service_chief')
        if msg:
            return False, msg

        # remove state
        list_states = ['proposed_to_service_chief']
        om_workflow.states.deleteStates(list_states)

        # change created transitions
        transitions = list(om_workflow.states['created'].transitions)
        transitions.remove('propose_to_service_chief')
        om_workflow.states['created'].transitions = tuple(transitions)
        # change to_be_signed transitions
        transitions = list(om_workflow.states['to_be_signed'].transitions)
        transitions.remove('back_to_service_chief')
        om_workflow.states['to_be_signed'].transitions = tuple(transitions)
        # remove transitions
        list_transitions = ['propose_to_service_chief', 'back_to_service_chief']
        om_workflow.transitions.deleteTransitions(list_transitions)

        # remove local roles
        fti = getUtility(IDexterityFTI, name='dmsoutgoingmail')
        lr = getattr(fti, 'localroles')
        changed_flag = False
        for lrgroup in lr:
            if 'proposed_to_service_chief' in lr[lrgroup]:
                del lr[lrgroup]['proposed_to_service_chief']
                changed_flag = True
        if changed_flag:
            lr._p_changed = True

        # disable collection
        folder = portal['outgoing-mail']['mail-searches']
        if folder['searchfor_proposed_to_service_chief'].enabled:
            folder['searchfor_proposed_to_service_chief'].enabled = False
            folder['searchfor_proposed_to_service_chief'].reindexObject()
            # update search collection list
            invalidate_cachekey_volatile_for('collective.eeafaceted.collectionwidget.cachedcollectionvocabulary')

        # update state list
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsoutgoingmail')

        return True, ''


SERVICE_VALIDATION_LEVELS = SimpleVocabulary([SimpleTerm(value=i) for i in range(1, 6)])


@provider(IContextSourceBinder)
def service_validation_levels(context):
    # must return not yet used levels
    return SERVICE_VALIDATION_LEVELS


class IIMServiceValidationParameters(Interface):

    validation_level = schema.Choice(
        title=u'Service validation level',
        required=True,
        source=service_validation_levels,
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
        default=u'',
        required=True,
    )


class IMServiceValidation(WorkflowAdaptationBase):

    schema = IIMServiceValidationParameters
    multiplicity = True

    def patch_workflow(self, workflow_name, **parameters):
        if not workflow_name == 'incomingmail_workflow':
            return False, _("incomingmail_workflow was not selected")
        portal = api.portal.get()
        wtool = portal.portal_workflow
        level = parameters['validation_level']
        wf = wtool['incomingmail_workflow']
        new_id = 'n_plus_{}'.format(level)
        new_state_id = 'proposed_to_{}'.format(new_id)
        transitions = ['back_to_creation', 'back_to_manager']
        if level == 1:
            # next = descending the validation to go to agent
            next_id = 'agent'
            transitions.append('close')
        else:
            next_id = 'n_plus_{}'.format(level-1)
        next_state_id = 'proposed_to_{}'.format(next_id)
        transitions.append('propose_to_{}'.format(next_id))

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
        propose_tr_id = 'propose_to_{}'.format(new_id)
        wf.transitions.addTransition(propose_tr_id)
        wf.transitions[propose_tr_id].setProperties(
            title=parameters['forward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=propose_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_propose_to_n_plus.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})
        back_tr_id = 'back_to_{}'.format(new_id)
        wf.transitions.addTransition(back_tr_id)
        wf.transitions[back_tr_id].setProperties(
            title=parameters['backward_transition_title'].encode('utf8'),
            new_state_id=new_state_id, trigger_type=1, script_name='',
            actbox_name=back_tr_id, actbox_url='',
            actbox_icon='%(portal_url)s/++resource++imio.dms.mail/im_back_to_n_plus.png',
            actbox_category='workflow',
            props={'guard_permissions': 'Review portal content'})

        # modify existing states
        next_state = wf.states[next_state_id]
        transitions = list(next_state.transitions)
        for tr in ('back_to_manager', 'back_to_creation'):
            if tr in transitions:
                transitions.remove(tr)
        transitions.append(back_tr_id)
        next_state.transitions = tuple(transitions)

        for st in ('proposed_to_manager', 'created'):
            previous_state = wf.states[st]
            transitions = list(previous_state.transitions)
            for tr in ('propose_to_{}'.format(next_id), 'close'):
                if tr in transitions:
                    transitions.remove(tr)
            transitions.append(propose_tr_id)
            previous_state.transitions = tuple(transitions)

        # add function
        functions = get_registry_functions()
        if new_id not in [fct['fct_id'] for fct in functions]:
            functions.append({'fct_title': parameters['function_title'], 'fct_id': unicode(new_id), 'fct_orgs': [],
                              'fct_management': False})
            set_registry_functions(functions)

        # add local roles config
        fti = getUtility(IDexterityFTI, name='dmsincomingmail')
        lr = getattr(fti, 'localroles')
        previous_states = ['proposed_to_n_plus_{}'.format(i) for i in range(1, level)]
        lrg = lr['treating_groups']
        if new_state_id not in lrg:
            lrg[new_state_id] = {new_id: {'roles': ['Contributor', 'Editor', 'Reviewer', 'Treating Group Writer']}}
            for st in previous_states:
                lrg[st].update({new_id: {'roles': ['Contributor', 'Editor', 'Reviewer']}})
            lrg['proposed_to_agent'].update({new_id: {'roles': ['Contributor', 'Editor', 'Reviewer']}})
            lrg['in_treatment'].update({new_id: {'roles': ['Contributor', 'Editor', 'Reviewer']}})
            lrg['closed'].update({new_id: {'roles': ['Reviewer']}})
        lrg = lr['recipient_groups']
        if new_state_id not in lrg:
            lrg[new_state_id] = {new_id: {'roles': ['Reader']}}
            for st in previous_states:
                lrg[st].update({new_id: {'roles': ['Reader']}})
            lrg['proposed_to_agent'].update({new_id: {'roles': ['Reader']}})
            lrg['in_treatment'].update({new_id: {'roles': ['Reader']}})
            lrg['closed'].update({new_id: {'roles': ['Reader']}})
        # We need to indicate that the object has been modified and must be 'saved'
        lr._p_changed = True

        # add collection
        folder = portal['incoming-mail']['mail-searches']
        col_id = 'searchfor_{}'.format(new_state_id)
        col_title = u'État: {}'.format(parameters['state_title'])
        if col_id not in folder:
            next_col = folder['searchfor_{}'.format(next_state_id)]
            folder.invokeFactory('DashboardCollection', id=col_id, title=col_title, enabled=True,
                                 query=[{'i': 'portal_type', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': ['dmsincomingmail']},
                                        {'i': 'review_state', 'o': 'plone.app.querystring.operation.selection.is',
                                         'v': [new_state_id]}],
                                 customViewFields=tuple(next_col.customViewFields),
                                 tal_condition=None,
                                 showNumberOfItems=False,
                                 roles_bypassing_talcondition=['Manager', 'Site Administrator'],
                                 sort_on=u'created', sort_reversed=True, b_size=30, limit=0)
            col = folder[col_id]
            col.setSubject((u'search', ))
            col.reindexObject(['Subject'])
            col.setLayout('tabular_view')
            folder.moveObjectToPosition(col_id, folder.getObjectPosition('searchfor_{}'.format(next_state_id)))

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

        # update state list
        invalidate_cachekey_volatile_for('imio.dms.mail.utils.list_wf_states.dmsincomingmail')

        # update actionspanel back transitions registry
        lst = api.portal.get_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions')
        if 'dmsincomingmail.{}|'.format(back_tr_id) not in lst:
            lst.append('dmsincomingmail.{}|'.format(back_tr_id))
            api.portal.set_registry_record('imio.actionspanel.browser.registry.IImioActionsPanelConfig.transitions',
                                           lst)

        return True, ''
