# -*- coding: utf-8 -*-

# Copyright (c) 2021 by Imio
# GNU General Public License (GPL)
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.contact.plonegroup.utils import get_suffixed_groups
from collective.documentgenerator.utils import update_templates
from collective.wfadaptations.api import add_applied_adaptation
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
from collective.wfadaptations.api import RECORD_NAME
from eea.facetednavigation.criteria.interfaces import ICriteria
from ftw.labels.interfaces import ILabeling
from imio.dms.mail import IM_READER_SERVICE_FUNCTIONS
from imio.dms.mail import OM_READER_SERVICE_FUNCTIONS
from imio.dms.mail.setuphandlers import add_templates
from imio.dms.mail.setuphandlers import list_templates
from imio.dms.mail.setuphandlers import update_task_workflow
from imio.dms.mail.utils import separate_fullname
from imio.dms.mail.wfadaptations import IMServiceValidation
from imio.dms.mail.wfadaptations import OMServiceValidation
from imio.dms.mail.wfadaptations import TaskServiceValidation
from imio.helpers.content import uuidToObject
from imio.helpers.workflow import load_workflow_from_package
from imio.pyutils.utils import append
from persistent.list import PersistentList
from plone import api
from Products.CMFPlone.utils import safe_unicode
from z3c.relationfield import RelationValue
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.intid import IIntIds
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import datetime
import logging
import os


logger = logging.getLogger('imio.dms.mail: steps')


def create_persons_from_users(portal, start='firstname', functions=['encodeur'], userid=''):
    """
        create own personnel from plone users
    """
    pf = portal['contacts']['personnel-folder']
    users = {}
    groups = api.group.get_groups()
    for group in groups:
        if '_' not in group.id or group.id in ['createurs_dossier', 'dir_general', 'lecteurs_globaux_ce',
                                               'lecteurs_globaux_cs']:
            continue
        parts = group.id.split('_')
        org_uid = function = None
        if len(parts) > 1:
            org_uid = parts[0]
            function = '_'.join(parts[1:])
        if function and function not in functions:
            continue
        for user in api.user.get_users(group=group):
            if userid and user.id != userid:
                continue
            if user.id not in users and user.id not in ['scanner']:
                users[user.id] = {'pers': {}, 'orgs': []}
                firstname, lastname = separate_fullname(user, start=start)
                users[user.id]['pers'] = {'lastname': lastname, 'firstname': firstname, 'email':
                                          safe_unicode(user.getProperty('email')), 'use_parent_address': False}
            if org_uid and org_uid not in users[user.id]['orgs']:
                users[user.id]['orgs'].append(org_uid)

    intids = getUtility(IIntIds)
    out = []
    # logger.info(users)
    for userid in users:
        email = users[userid]['pers'].pop('email')
        exist = portal.portal_catalog.unrestrictedSearchResults(mail_type=userid, portal_type='person')
        if userid in pf:
            pers = pf[userid]
        elif exist:
            pers = exist[0]._unrestrictedGetObject()
        else:
            out.append(u"person created for user %s, fn:'%s', ln:'%s'" % (userid, users[userid]['pers']['firstname'],
                                                                          users[userid]['pers']['lastname']))
            logger.info(out[-1])
            pers = api.content.create(container=pf, type='person', id=userid, userid=userid, **users[userid]['pers'])
        if api.content.get_state(pers) == 'deactivated':
            api.content.transition(pers, 'activate')
        hps = [b._unrestrictedGetObject() for b in
               portal.portal_catalog.unrestrictedSearchResults(path='/'.join(pers.getPhysicalPath()),
                                                               portal_type='held_position')]
        orgs = dict([(hp.get_organization(), hp) for hp in hps])
        for uid in users[userid]['orgs']:
            org = uuidToObject(uid, unrestricted=True)
            if not org:
                continue
            if uid in pers:
                hp = pers[uid]
            elif org in orgs:
                hp = orgs[org]
            else:
                out.append(u" -> hp created with org '%s'" % org.get_full_title())
                logger.info(out[-1])
                hp = api.content.create(container=pers, id=uid, type='held_position', **{'email': email,
                                        'position': RelationValue(intids.getId(org)), 'use_parent_address': True})
            if api.content.get_state(hp) == 'deactivated':
                api.content.transition(hp, 'activate')
    return out


# #############
# Singles steps
# #############

def create_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    add_templates(context.getSite())


def update_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    templates_list = [(tup[1], tup[2]) for tup in list_templates()]
    ret = update_templates(templates_list)
    ret = '\n'.join(["%s: %s" % (tup[0], tup[2]) for tup in ret]).encode('utf8')
    logger.info('\n{}'.format(ret))
    return ret


def override_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    templates_list = [(tup[1], tup[2]) for tup in list_templates()]
    ret = update_templates(templates_list, force=True)
    ret = '\n'.join(["%s: %s" % (tup[0], tup[2]) for tup in ret]).encode('utf8')
    logger.info('\n{}'.format(ret))
    return ret


def create_persons_from_users_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    return '\n'.join(create_persons_from_users(context.getSite())).encode('utf8')


def create_persons_from_users_step_inverted(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    return '\n'.join(create_persons_from_users(context.getSite(), start='lastname')).encode('utf8')


def add_icons_to_contact_workflow(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    wfl = site.portal_workflow.collective_contact_core_workflow
    for name, icon in (('activate', 'im_treat'), ('deactivate', 'im_back_to_creation')):
        tr = wfl.transitions.get(name)
        tr.actbox_icon = '%%(portal_url)s/++resource++imio.dms.mail/%s.png' % icon


def mark_copy_im_as_read(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    # adapted = ILabelJar(site['incoming-mail']); adapted.list()
    days_back = 5
    start = datetime.datetime(1973, 2, 12)
    end = datetime.datetime.now() - datetime.timedelta(days=days_back)
    users = {}
    functions = {'i': IM_READER_SERVICE_FUNCTIONS, 'o': OM_READER_SERVICE_FUNCTIONS}
    brains = site.portal_catalog.unrestrictedSearchResults(portal_type=['dmsincomingmail', 'dmsincoming_email'],
                                                           created={'query': (start, end), 'range': 'min:max'},
                                                           sort_on='created')
    out = ["%d mails" % len(brains)]
    changed_mails = 0
    related_users = set()
    for brain in brains:
        if not brain.recipient_groups:
            continue
        typ = brain.portal_type[3:4]
        user_ids = set()
        for org_uid in brain.recipient_groups:
            if org_uid not in users:
                users[org_uid] = {}
            if typ not in users[org_uid]:
                users[org_uid][typ] = [u.id for u in get_selected_org_suffix_users(org_uid, functions[typ])]
            for userid in users[org_uid][typ]:
                user_ids.add(userid)
        if len(user_ids):
            related_users.update(user_ids)
            obj = brain._unrestrictedGetObject()
            labeling = ILabeling(obj)
            labeling.storage['lu'] = PersistentList(user_ids)
            obj.reindexObject(idxs=['labels'])
            changed_mails += 1
    out.append('%d mails labelled with "lu"' % changed_mails)
    out.append('%d users are concerned' % len(related_users))
    return '\n'.join(out)


def im_n_plus_1_wfadaptation(context):
    """
        Add n_plus_1 level in incomingmail_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info('Apply n_plus_1 level on incomingmail_workflow')
    site = context.getSite()
    n_plus_1_params = {'validation_level': 1, 'state_title': u'À valider par le chef de service',
                       'forward_transition_title': u'Proposer au chef de service',
                       'backward_transition_title': u'Renvoyer au chef de service',
                       'function_title': u'N+1'}
    sva = IMServiceValidation()
    adapt_is_applied = sva.patch_workflow('incomingmail_workflow', **n_plus_1_params)
    if adapt_is_applied:
        add_applied_adaptation('imio.dms.mail.wfadaptations.IMServiceValidation',
                               'incomingmail_workflow', True, **n_plus_1_params)
    # Add users to activated groups
    if 'chef' in [u.id for u in api.user.get_users()]:
        for uid in get_registry_organizations():
            site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_n_plus_1" % uid)


def om_n_plus_1_wfadaptation(context):
    """
        Add n_plus_1 level in outgoingmail_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info('Apply n_plus_1 level on outgoingmail_workflow')
    site = context.getSite()
    n_plus_1_params = {'validation_level': 1, 'state_title': u'À valider par le chef de service',
                       'forward_transition_title': u'Proposer au chef de service',
                       'backward_transition_title': u'Renvoyer au chef de service',
                       'function_title': u'N+1',
                       'validated_from_created': False}
    sva = OMServiceValidation()
    adapt_is_applied = sva.patch_workflow('outgoingmail_workflow', **n_plus_1_params)
    if adapt_is_applied:
        add_applied_adaptation('imio.dms.mail.wfadaptations.OMServiceValidation',
                               'outgoingmail_workflow', True, **n_plus_1_params)
    # Add users to activated groups
    if 'chef' in [u.id for u in api.user.get_users()]:
        for uid in get_registry_organizations():
            site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_n_plus_1" % uid)


def task_n_plus_1_wfadaptation(context):
    """
        Add n_plus_1 level in task_workflow
    """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info('Apply n_plus_1 level on task_workflow')
    site = context.getSite()
    sva = TaskServiceValidation()
    adapt_is_applied = sva.patch_workflow('task_workflow', **{})
    if adapt_is_applied:
        add_applied_adaptation('imio.dms.mail.wfadaptations.TaskServiceValidation',
                               'task_workflow', True, **{})
    # Add users to activated groups
    if 'chef' in [u.id for u in api.user.get_users()]:
        for uid in get_registry_organizations():
            site.acl_users.source_groups.addPrincipalToGroup('chef', "%s_n_plus_1" % uid)


def manage_classification(context, active):
    """Activate or deactivate classification"""
    logger.info('Manage classification by {}activating related things'.format(not active and 'de-' or ''))
    site = context.getSite()
    # handle navtree_properties
    unlisted = list(site.portal_properties.navtree_properties.metaTypesNotToList)
    update = False
    for ptype in ('ClassificationFolders', 'ClassificationContainer'):
        if active and ptype in unlisted:
            unlisted.remove(ptype)
            update = True
        elif not active and ptype not in unlisted:
            unlisted.append(ptype)
            update = True
    if update:
        site.portal_properties.navtree_properties.manage_changeProperties(metaTypesNotToList=unlisted)
    # handle fields
    for rec in ('imail_fields', 'omail_fields'):
        update = False
        rec_name = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(rec)
        showed = api.portal.get_registry_record(rec_name, default=[])
        showed_ids = [dic['field_name'] for dic in showed]
        # imf = [ for v in im_fo]
        for fld in (u'IClassificationFolder.classification_folders',
                    u'IClassificationFolder.classification_categories'):
            if active and fld not in showed_ids:
                idx = showed_ids.index('internal_reference_no')
                showed.insert(idx, {"field_name": fld, "read_tal_condition": u"", "write_tal_condition": u""})
                update = True
            elif not active and fld in showed_ids:
                showed = [dic for dic in showed if dic['field_name'] != fld]
                update = True
        if update:
            api.portal.set_registry_record(rec_name, list(showed))
    # handle criterias
    for dpath, crit_ids in (('incoming-mail', ['c20', 'c21']), ('outgoing-mail', ['c19', 'c20'])):
        mspath = os.path.join(dpath, 'mail-searches')
        folder = site.unrestrictedTraverse(mspath)
        criterias = ICriteria(folder)
        for crit_id in crit_ids:
            criterion = criterias.get(crit_id)
            if active and criterion.hidden:
                criterion.hidden = False
                criterias.criteria._p_changed = 1
            elif not active and not criterion.hidden:
                criterion.hidden = True
                criterias.criteria._p_changed = 1
    # handle columns
    for dpath in ('incoming-mail', 'outgoing-mail'):
        obj = site.unrestrictedTraverse(dpath)
        brains = site.portal_catalog(portal_type='DashboardCollection', path='/'.join(obj.getPhysicalPath()))
        for brain in brains:
            col = brain.getObject()
            buf = list(col.customViewFields)
            if active and u'classification_folders' not in buf:
                if 'actions' in buf:
                    buf.insert(buf.index('actions'), u'classification_folders')
                else:
                    buf.append(u'classification_folders')
                col.customViewFields = tuple(buf)
            elif not active and u'classification_folders' in buf:
                buf.remove(u'classification_folders')
                col.customViewFields = tuple(buf)


def deactivate_classification(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    manage_classification(context, False)


def activate_classification(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    manage_classification(context, True)


def reset_workflows_bad(context):
    """Reset workflows and reapply wf adaptations."""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    # TODO
    # find what's deleted (with local roles config or collection ?)
    # reset dms_config
    # clean local roles
    # delete collection
    # clean registry with prefix prefix:imio.actionspanel.browser.registry.IImioActionsPanelConfig
    # clean remark config
    # clean function if all removed ?
    # reindex

    site.portal_setup.runImportStepFromProfile('profile-imio.dms.mail:default', 'workflow', run_dependencies=False)
    applied_adaptations = [dic['adaptation'] for dic in get_applied_adaptations()]
    if applied_adaptations:
        success, errors = apply_from_registry(reapply=True)
        if errors:
            logger.error("Problem applying wf adaptations: %d errors" % errors)
    if 'imio.dms.mail.wfadaptations.TaskServiceValidation' not in applied_adaptations:
        update_task_workflow(site)
    site.portal_workflow.updateRoleMappings()
    logger.info("Workflow reset done")


def remove_om_nplus1_wfadaptation(context):
    """"""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    val_state_id = 'validated'
    new_state_id = 'proposed_to_n_plus_1'
    log = []
    site = context.getSite()
    applied_adaptations = [dic['adaptation'] for dic in get_applied_adaptations()]
    # are there oms ?
    brains = site.portal_catalog.unrestrictedSearchResults(portal_type='dmsoutgoingmail',
                                                           review_state=[val_state_id, new_state_id])
    if brains:
        logger.error(append(log, "Found some outgoing mails in state 'proposed_to_n_plus_1' or 'validated'. We stop !"))
        return '\n'.join(log)
    # reset workflow
    if not load_workflow_from_package('outgoingmail_workflow', 'profile-imio.dms.mail:default'):
        raise Exception("Cannot reload workflow from package")
    # remove function if not used elsewhere
    functions = get_registry_functions()
    for wfa in (u'imio.dms.mail.wfadaptations.TaskServiceValidation',
                u'imio.dms.mail.wfadaptations.IMServiceValidation'):
        if wfa in applied_adaptations:
            logger.info(append(log, "Do not remove n_plus_1 function because it's used by another adaptation"))
            break
    else:
        if u'n_plus_1' in [fct['fct_id'] for fct in functions]:
            set_registry_functions([fct for fct in functions if fct['fct_id'] != u'n_plus_1'])
        # empty and delete groups...
        groups = get_suffixed_groups(['n_plus_1'])
        for group in groups:
            for user in api.user.get_users(group=group):
                api.group.remove_user(group=group, user=user)
            api.group.delete(group=group)
    # remove dexterity local roles om, folders
    # update dms config
    # remove collections, update some
    # update cache
    # update remark states
    # reindex
    # remove wfadaptation entry
    Not yet finished
    record = api.portal.get_registry_record(RECORD_NAME)
    api.portal.set_registry_record(RECORD_NAME, [d for d in record if d['adaptation'] !=
                                                 u'imio.dms.mail.wfadaptations.OMServiceValidation'])
    return '\n'.join(log)


def configure_wsclient(context):
    """ Configure wsclient """
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    site = context.getSite()
    logger.info('Configure wsclient step')
    log = ['Installing imio.pm.wsclient']
    site.portal_setup.runAllImportStepsFromProfile('profile-imio.pm.wsclient:default')

    log.append('Defining settings')
    prefix = 'imio.pm.wsclient.browser.settings.IWS4PMClientSettings'
    if not api.portal.get_registry_record('{}.pm_url'.format(prefix), default=False):
        pmurl = gedurl = os.getenv('PUBLIC_URL', '')
        pmurl = pmurl.replace('-ged', '-pm')
        if pmurl != gedurl:
            api.portal.set_registry_record('{}.pm_url'.format(prefix), u'{}/ws4pm.wsdl'.format(pmurl))
        api.portal.set_registry_record('{}.pm_username'.format(prefix), u'admin')
        pmpass = os.getenv('PM_PASS', '')  # not used
        if pmpass:
            api.portal.set_registry_record('{}.pm_password'.format(prefix), pmpass)
        api.portal.set_registry_record('{}.only_one_sending'.format(prefix), True)
        from imio.pm.wsclient.browser.vocabularies import pm_item_data_vocabulary
        orig_call = pm_item_data_vocabulary.__call__
        pm_item_data_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary([SimpleTerm(u'title'),
                                                                                SimpleTerm(u'description'),
                                                                                SimpleTerm(u'detailedDescription'),
                                                                                SimpleTerm(u'annexes')])
        api.portal.set_registry_record('{}.field_mappings'.format(prefix),
                                       [{'field_name': u'title', 'expression': u'context/title'},
                                        {'field_name': u'description',
                                         'expression': u"python: u'{}\\n{}'.format(context.description, "
                                                       u"context.restrictedTraverse('@@IncomingmailWSClient')"
                                                       u".detailed_description())"},
                                        # {'field_name': u'detailedDescription',
                                        #  'expression': u'context/@@IncomingmailWSClient/detailed_description'},
                                        {'field_name': u'annexes',
                                         'expression': u'context/@@IncomingmailWSClient/get_main_files'},
                                        ])
        # u'string: ${context/@@ProjectWSClient/description}<br />${context/@@ProjectWSClient/detailed_description}'
        pm_item_data_vocabulary.__call__ = orig_call
        # api.portal.set_registry_record('{}.user_mappings'.format(prefix),
        #                                [{'local_userid': u'admin', 'pm_userid': u'dgen'}])
        from imio.pm.wsclient.browser.vocabularies import pm_meeting_config_id_vocabulary
        orig_call = pm_meeting_config_id_vocabulary.__call__
        pm_meeting_config_id_vocabulary.__call__ = lambda self, ctxt: SimpleVocabulary(
            [SimpleTerm(u'meeting-config-college')])
        from imio.dms.mail.subscribers import wsclient_configuration_changed
        from plone.registry.interfaces import IRecordModifiedEvent
        gsm = getGlobalSiteManager()
        gsm.unregisterHandler(wsclient_configuration_changed, (IRecordModifiedEvent, ))
        api.portal.set_registry_record('{}.generated_actions'.format(prefix),
                                       [{'pm_meeting_config_id': u'meeting-config-college',
                                         'condition': u"python: context.getPortalTypeName() in ('dmsincomingmail', "
                                                      u"'dmsincoming_email')",
                                         'permissions': 'Modify view template'}])
        api.portal.set_registry_record('{}.viewlet_display_condition'.format(prefix), u'isLinked')
        pm_meeting_config_id_vocabulary.__call__ = orig_call
        gsm.registerHandler(wsclient_configuration_changed, (IRecordModifiedEvent, ))
    [logger.info(msg) for msg in log]
    return '\n'.join(log)


def contact_import_pipeline(context):
    """Set contact import pipeline record."""
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    logger.info('Set contact import pipeline')
    api.portal.set_registry_record(
        'collective.contact.importexport.interfaces.IPipelineConfiguration.pipeline', u"""[transmogrifier]
pipeline =
    initialization
    csv_disk_source
#    csv_ssh_source
    csv_reader
    common_input_checks
    plonegrouporganizationpath
    plonegroupinternalparent
#    iadocs_inbw_subtitle
    dependencysorter
#    stop
    relationsinserter
    updatepathinserter
    parentpathinserter
    moveobject
    pathinserter
#    iadocs_inbw_merger
    constructor
    iadocs_userid
#    iadocs_creating_group
    schemaupdater
    reindexobject
    transitions_inserter
    workflowupdater
    breakpoint
    short_log
#    logger
    lastsection

# mandatory section !
[config]
# needed if contact encoding group is enabled in Plone
creating_group =
# if empty, first found directory is used. Else relative path in portal
directory_path =
csv_encoding = utf8
# needed if plone-group organization is imported
plonegroup_org_title =
organizations_filename =
organizations_fieldnames = _id _oid title description organization_type use_parent_address street number additional_address_details zip_code city phone cell_phone fax email website region country enterprise_number internal_number _uid _ic
persons_filename =
persons_fieldnames = _id lastname firstname gender person_title birthday use_parent_address street number additional_address_details zip_code city phone cell_phone fax email website region country internal_number _uid _ic
held_positions_filename =
held_positions_fieldnames = _id _pid _oid _fid label start_date end_date use_parent_address street number additional_address_details zip_code city phone cell_phone fax email website region country internal_number _uid _ic
raise_on_error = 1

[initialization]
blueprint = collective.contact.importexport.init
# basepath is an absolute directory. If empty, buildout dir will be used
basepath =
# if subpath, it will be appended to basepath
subpath = imports

[csv_disk_source]
blueprint = collective.contact.importexport.csv_disk_source
organizations_filename = ${config:organizations_filename}
persons_filename = ${config:persons_filename}
held_positions_filename = ${config:held_positions_filename}

[csv_ssh_source]
blueprint = collective.contact.importexport.csv_ssh_source
servername = sftp-client.imio.be
username =
server_files_path = .../upload_success
registry_filename = 0_registry.dump
transfer_path = copied

[csv_reader]
blueprint = collective.contact.importexport.csv_reader
fmtparam-strict = python:True
# fmtparam-delimiter = python:';'
csv_headers = python:True
raise_on_error = ${config:raise_on_error}

[common_input_checks]
blueprint = collective.contact.importexport.common_input_checks
phone_country = BE
language = fr
organization_uniques = _uid internal_number
organization_booleans = use_parent_address _ic _inactive
organization_hyphen_newline = title street
person_uniques = _uid internal_number
person_booleans = use_parent_address _ic _inactive
held_position_uniques = _uid
held_position_booleans = use_parent_address _ic _inactive
raise_on_error = ${config:raise_on_error}

[plonegrouporganizationpath]
blueprint = imio.transmogrifier.contact.plonegrouporganizationpath
plonegroup_org_title = ${config:plonegroup_org_title}

[plonegroupinternalparent]
blueprint = imio.transmogrifier.contact.plonegroupinternalparent

[iadocs_inbw_subtitle]
blueprint = imio.transmogrifier.contact.iadocs_inbw_subtitle_updater

[dependencysorter]
blueprint = collective.contact.importexport.dependencysorter

[relationsinserter]
blueprint = collective.contact.importexport.relationsinserter
raise_on_error = ${config:raise_on_error}

[updatepathinserter]
blueprint = collective.contact.importexport.updatepathinserter
# list of 'column' 'index name' 'item condition' 'must-exist' quartets used to search in catalog for an existing object
organization_uniques = _uid UID python:True python:True internal_number internal_number python:True python:False
person_uniques = _uid UID python:True python:True internal_number mail_type python:item['_ic'] python:False internal_number internal_number python:True python:False
held_position_uniques = _uid UID python:True python:True
raise_on_error = ${config:raise_on_error}

[parentpathinserter]
blueprint = collective.contact.importexport.parentpathinserter
raise_on_error = ${config:raise_on_error}

[moveobject]
blueprint = collective.contact.importexport.moveobject
raise_on_error = ${config:raise_on_error}

[pathinserter]
blueprint = collective.contact.importexport.pathinserter
organization_id_keys = title
person_id_keys = firstname lastname
held_position_id_keys = label
raise_on_error = ${config:raise_on_error}

[iadocs_inbw_merger]
blueprint = imio.transmogrifier.contact.iadocs_inbw_merger
raise_on_error = ${config:raise_on_error}

[constructor]
blueprint = collective.transmogrifier.sections.constructor

[iadocs_userid]
blueprint = imio.transmogrifier.contact.iadocs_userid_inserter
raise_on_error = ${config:raise_on_error}

[iadocs_creating_group]
blueprint = imio.transmogrifier.contact.iadocs_creating_group_inserter
creating_group = ${config:creating_group}

[schemaupdater]
blueprint = transmogrify.dexterity.schemaupdater

[reindexobject]
blueprint = plone.app.transmogrifier.reindexobject

[transitions_inserter]
blueprint = collective.contact.importexport.transitions_inserter

[workflowupdater]
blueprint = plone.app.transmogrifier.workflowupdater

[short_log]
blueprint = collective.contact.importexport.short_log

[lastsection]
blueprint = collective.contact.importexport.lastsection
send_mail = 1

[logger]
blueprint = collective.transmogrifier.sections.logger
name = logger
level = INFO
delete =
    _oid
    title
    description
    organization_type
    use_parent_address
    street
    number
    additional_address_details
    zip_code
    city
    phone
    cell_phone
    fax
    email
    website
    region
    country
    internal_number
    _uid
    _ic
    lastname
    firstname
    gender
    person_title
    birthday
    _pid
    _fid
    label
    start_date
    end_date
    position
    userid
    _files
    _level
    _ln
    _parent
    _typ

[breakpoint]
blueprint = collective.contact.importexport.breakpoint
condition = python:item.get('_id', u'') == u'0'

[stop]
blueprint = collective.contact.importexport.stop
condition = python:True
""")  # noqa: E501
