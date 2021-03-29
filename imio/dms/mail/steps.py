# -*- coding: utf-8 -*-

# Copyright (c) 2021 by Imio
# GNU General Public License (GPL)
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.documentgenerator.utils import update_templates
from collective.wfadaptations.api import add_applied_adaptation
from collective.wfadaptations.api import apply_from_registry
from collective.wfadaptations.api import get_applied_adaptations
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
from persistent.list import PersistentList
from plone.app.uuid.utils import uuidToObject
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


logger = logging.getLogger('imio.dms.mail: setuphandlers')


def create_persons_from_users(portal, start='firstname', functions=['encodeur'], userid=''):
    """
        create own personnel from plone users
    """
    pf = portal['contacts']['personnel-folder']
    users = {}
    groups = api.group.get_groups()
    for group in groups:
        if '_' not in group.id or group.id in ['dir_general', 'lecteurs_globaux_ce', 'lecteurs_globaux_cs']:
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
        exist = portal.portal_catalog(mail_type=userid, portal_type='person')
        if userid in pf:
            pers = pf[userid]
        elif exist:
            pers = exist[0].getObject()
        else:
            out.append(u"person created for user %s, fn:'%s', ln:'%s'" % (userid, users[userid]['pers']['firstname'],
                                                                          users[userid]['pers']['lastname']))
            logger.info(out[-1])
            pers = api.content.create(container=pf, type='person', id=userid, userid=userid, **users[userid]['pers'])
        if api.content.get_state(pers) == 'deactivated':
            api.content.transition(pers, 'activate')
        hps = [b.getObject() for b in api.content.find(context=pers, portal_type='held_position')]
        orgs = dict([(hp.get_organization(), hp) for hp in hps])
        for uid in users[userid]['orgs']:
            org = uuidToObject(uid)
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
    return '\n'.join(["%s: %s" % (tup[0], tup[2]) for tup in ret]).encode('utf8')


def override_templates_step(context):
    if not context.readDataFile("imiodmsmail_singles_marker.txt"):
        return
    templates_list = [(tup[1], tup[2]) for tup in list_templates()]
    ret = update_templates(templates_list, force=True)
    return '\n'.join(["%s: %s" % (tup[0], tup[2]) for tup in ret]).encode('utf8')


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
    DAYS_BACK = 5
    start = datetime.datetime(1973, 02, 12)
    end = datetime.datetime.now() - datetime.timedelta(days=DAYS_BACK)
    users = {}
    functions = {'i': IM_READER_SERVICE_FUNCTIONS, 'o': OM_READER_SERVICE_FUNCTIONS}
    brains = site.portal_catalog(portal_type=['dmsincomingmail', 'dmsincoming_email'],
                                 created={'query': (start, end), 'range': 'min:max'},
                                 sort_on='created')
    out = []
    out.append("%d mails" % len(brains))
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
            obj = brain.getObject()
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
                       'function_title': u'N+1'}
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


def reset_workflows(context):
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
                                         'condition': u"python: context.getPortalTypeName() in ('dmsincomingmail', )",
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
    site = context.getSite()
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
held_positions_fieldnames = _id _pid _oid _fid label start_date end_date use_parent_address street number additional_address_details zip_code city phone cell_phone fax email website region country _uid _ic
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
transfer_path = imports/copied

[csv_reader]
blueprint = collective.contact.importexport.csv_reader
fmtparam-strict = python:True
csv_headers = python:True
raise_on_error = ${config:raise_on_error}

[common_input_checks]
blueprint = collective.contact.importexport.common_input_checks
phone_country = BE
language = fr
organization_uniques = _uid internal_number
organization_booleans = use_parent_address _ic _inactive
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
