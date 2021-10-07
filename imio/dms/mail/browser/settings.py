# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.wfadaptations.api import get_applied_adaptations
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from dexterity.localroles.utils import add_fti_configuration
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail.utils import list_wf_states
from imio.dms.mail.utils import reimport_faceted_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import get_schema_fields
from natsort import humansorted
from operator import attrgetter
from plone import api
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.app.z3cform.wysiwyg import WysiwygFieldWidget
from plone.autoform.directives import widget
from plone.dexterity.fti import DexterityFTIModificationDescription
from plone.dexterity.fti import ftiModified
from plone.dexterity.interfaces import IDexterityFTI
from plone.registry.interfaces import IRecordModifiedEvent
from plone.supermodel import model
from plone.z3cform import layout
from z3c.form import form
from z3c.form.browser.orderedselect import OrderedSelectFieldWidget
# from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.component import getUtility
from zope.interface import implements
from zope.interface import Interface
from zope.interface import Invalid
# from zope.interface import provider
# from zope.schema.interfaces import IContextSourceBinder
from zope.interface import invariant
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import copy
import logging


logger = logging.getLogger('imio.dms.mail: settings')


def get_pt_fields_voc(pt, excluded):
    terms = []
    for name, field in get_schema_fields(type_name=pt, prefix=True):
        if name in excluded:
            continue
        terms.append(SimpleTerm(name, title=_tr(field.title)))
    return SimpleVocabulary(humansorted(terms, key=attrgetter('title')))


# @provider(IContextSourceBinder)
# def IMFields(context):
class IMFieldsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return get_pt_fields_voc('dmsincomingmail',  # i_e ok
                                 ['IDublinCore.contributors', 'IDublinCore.creators', 'IDublinCore.effective',
                                  'IDublinCore.expires', 'IDublinCore.language', 'IDublinCore.rights',
                                  'IDublinCore.subjects', 'INameFromTitle.title', 'ITask.assigned_group',
                                  'ITask.enquirer', 'IVersionable.changeNote', 'notes', 'recipients', 'related_docs'])


class OMFieldsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return get_pt_fields_voc('dmsoutgoingmail',
                                 ['IDublinCore.contributors', 'IDublinCore.creators', 'IDublinCore.effective',
                                  'IDublinCore.expires', 'IDublinCore.language', 'IDublinCore.rights',
                                  'IDublinCore.subjects', 'INameFromTitle.title', 'ITask.assigned_group',
                                  'ITask.enquirer', 'IVersionable.changeNote', 'notes', 'related_docs'])


class IIMFieldsSchema(Interface):
    field_name = schema.Choice(
        title=_(u'Field name'),
        vocabulary=u'imio.dms.mail.IMFieldsVocabulary',
    )

    read_tal_condition = schema.TextLine(
        title=_("Read TAL condition"),
        required=False,
    )

    write_tal_condition = schema.TextLine(
        title=_("Write TAL condition"),
        required=False,
    )


class IOMFieldsSchema(Interface):
    field_name = schema.Choice(
        title=_(u'Field name'),
        vocabulary=u'imio.dms.mail.OMFieldsVocabulary',
    )

    read_tal_condition = schema.TextLine(
        title=_("Read TAL condition"),
        required=False,
    )

    write_tal_condition = schema.TextLine(
        title=_("Write TAL condition"),
        required=False,
    )


assigned_user_check_levels = SimpleVocabulary(
    [
        SimpleTerm(value=u'no_check', title=_(u'No check')),
        SimpleTerm(value=u'n_plus_1', title=_(u'Assigned user mandatory only if there is a n+1 validation')),
        SimpleTerm(value=u'mandatory', title=_(u'Assigned user always mandatory'))
    ]
)

fullname_forms = SimpleVocabulary(
    [
        SimpleTerm(value=u'firstname', title=_(u'Firstname Lastname')),
        SimpleTerm(value=u'lastname', title=_(u'Lastname Firstname'))
    ]
)

iemail_manual_forward_transitions = SimpleVocabulary(
    [
        SimpleTerm(value=u'created', title=_(u'A user forwarded email will stay at creation level')),
        SimpleTerm(value=u'manager', title=_(u'A user forwarded email will go to manager level')),
        SimpleTerm(value=u'n_plus_h', title=_(u'A user forwarded email will go to highest N+ level, '
                                              u'otherwise to agent')),
        SimpleTerm(value=u'n_plus_l', title=_(u'A user forwarded email will go to lowest N+ level, '
                                              u'otherwise to agent')),
        SimpleTerm(value=u'agent', title=_(u'A user forwarded email will go to agent level')),
    ]
)


class ITableListSchema(Interface):
    value = schema.TextLine(title=_("Stored value/id"), required=True)
    dtitle = schema.TextLine(title=_("Displayed title"), required=True)
    active = schema.Bool(title=_("Active"), required=False)


class IImioDmsMailConfig(model.Schema):
    """
    Configuration of dms mail
    """

    model.fieldset(
        'incomingmail',
        label=_(u'Incoming mail'),
        fields=['mail_types', 'assigned_user_check', 'original_mail_date_required', 'due_date_extension',
                'imail_remark_states', 'imail_fields', 'imail_group_encoder']
    )

    mail_types = schema.List(
        title=_(u'Types of incoming mail'),
        description=_(u"Once created and used, value doesn't be changed anymore. None can be used for a 'choose' "
                      u"value."),
        value_type=DictRow(title=_("Mail type"),
                           schema=ITableListSchema))

    widget('mail_types', DataGridFieldFactory, allow_reorder=True)

    assigned_user_check = schema.Choice(
        title=_(u'Assigned user check'),
        description=_(u'Check if there is an assigned user before proposing incoming mail to an agent.'),
        vocabulary=assigned_user_check_levels,
        default=u'n_plus_1'
    )

    original_mail_date_required = schema.Bool(
        title=_(u'Original mail date requirement'),
        description=_(u"Check if the incoming mail 'original mail date' field must be required."),
        default=True
    )

    due_date_extension = schema.Int(
        title=_(u'Due date extension'),
        description=_(u'Extends the due date by a number of days. 0 means no due date will be set by default.'),
        default=0,
        min=0
    )

    imail_remark_states = schema.List(
        title=_(u"States for which to display remark icon"),
        value_type=schema.Choice(vocabulary=u'imio.dms.mail.IMReviewStatesVocabulary'),
    )

    imail_fields = schema.List(
        title=_(u"${type} fields display", mapping={'type': _('Incoming mail')}),
        description=_(u"Configure this carefully. You can order with arrows."),
        required=False,
        value_type=DictRow(title=_(u'Field'), schema=IIMFieldsSchema, required=False),
    )
    widget(
        'imail_fields',
        DataGridFieldFactory,
        display_table_css_class='listing',
        allow_reorder=True,
        auto_append=False,
    )

    imail_group_encoder = schema.Bool(
        title=_(u'Activate group encoder'),
        description=_(u"ONCE ACTIVATED, THIS OPTION CAN'T BE EASILY UNDONE !! <br />"
                      u"When activating this option, a group encoder function is added in the configuration, "
                      u"a new field is added to the mail form to choose the creating group and permissions are given "
                      u"to the selected creating group. Mails are then separately handled following the creating "
                      u"groups. <br />The creating group can be preset in scanning program. It's then possible to have "
                      u"multiple scanners and separated 'encoder' groups. "
                      u"The list of 'encoder' groups, can be generated to be used in 'scanner program'."),
        default=False
    )

    model.fieldset(
        'incoming_email',
        label=_(u'Incoming email'),
        fields=['iemail_manual_forward_transition']
    )

    iemail_manual_forward_transition = schema.Choice(
        title=_(u'Email manual forward transition'),
        description=_(u'Choose to which state a manually forwarded email will go.'),
        vocabulary=iemail_manual_forward_transitions,
        default=u'agent'
    )

    model.fieldset(
        'outgoingmail',
        label=_(u'Outgoing mail'),
        fields=['omail_types', 'omail_remark_states', 'omail_response_prefix', 'omail_odt_mainfile',
                'omail_sender_firstname_sorting', 'org_templates_encoder_can_edit',
                'org_email_templates_encoder_can_edit', 'omail_fullname_used_form', 'omail_send_modes',
                'omail_close_on_email_send', 'omail_email_signature', 'omail_fields', 'omail_group_encoder']
    )

    omail_types = schema.List(
        title=_(u'Types of outgoing mail'),
        description=_(u"Once created and used, value doesn't be changed anymore. None can be used for a 'choose' "
                      u"value."),
        value_type=DictRow(title=_("Mail type"),
                           schema=ITableListSchema))

    widget('omail_types', DataGridFieldFactory, allow_reorder=True)

    omail_remark_states = schema.List(
        title=_(u"States for which to display remark icon"),
        value_type=schema.Choice(vocabulary=u'imio.dms.mail.OMReviewStatesVocabulary'),
    )

    omail_response_prefix = schema.TextLine(
        title=_("Response prefix"),
        required=False
    )

    omail_odt_mainfile = schema.Bool(
        title=_(u'Dms file must be an odt format'),
        default=True
    )

    omail_sender_firstname_sorting = schema.Bool(
        title=_(u'Sender list is sorted on firstname'),
        default=True
    )

    org_templates_encoder_can_edit = schema.Bool(
        title=_(u'Enable edition of service office templates for encoder'),
        description=_(u"Check if a service encoder can edit his service office templates."),
        default=True
    )

    org_email_templates_encoder_can_edit = schema.Bool(
        title=_(u'Enable edition of service email templates for encoder'),
        description=_(u"Check if a service encoder can edit his service email templates."),
        default=True
    )

    omail_fields = schema.List(
        title=_(u"${type} fields display", mapping={'type': _('Outgoing mail')}),
        description=_(u"Configure this carefully. You can order with arrows."),
        required=False,
        value_type=DictRow(title=_(u'Field'), schema=IOMFieldsSchema, required=False),
    )
    widget(
        'omail_fields',
        DataGridFieldFactory,
        display_table_css_class='listing',
        allow_reorder=True,
        auto_append=False,
    )

    omail_fullname_used_form = schema.Choice(
        title=_(u"User fullname used format"),
        vocabulary=fullname_forms,
        default='firstname',
    )

    omail_send_modes = schema.List(
        title=_(u'Send modes'),
        description=_(u"Once created and used, value doesn't be changed anymore. "
                      u"None can be used for a 'choose' value."),
        value_type=DictRow(title=_("Send modes"),
                           schema=ITableListSchema))

    widget('omail_send_modes', DataGridFieldFactory, allow_reorder=True)

    omail_close_on_email_send = schema.Bool(
        title=_(u'Close outgoing mail on email send'),
        default=True
    )

    widget('omail_email_signature', WysiwygFieldWidget)
    # widget('omail_email_signature', klass='pat-tinymce') in plone 5 ?
    omail_email_signature = schema.Text(
        title=_(u'Email signature model'),
        description=_(u'TAL compliant with variables: view, context, user, dghv, sender, request and modules.'),
        required=False,
    )

    omail_group_encoder = schema.Bool(
        title=_(u'Activate group encoder'),
        description=_(u"ONCE ACTIVATED, THIS OPTION CAN'T BE EASILY UNDONE !! <br />"
                      u"When activating this option, a group encoder function is added in the configuration, "
                      u"a new field is added to the mail form to choose the creating group and permissions are given "
                      u"to the selected creating group. Mails are then separately handled following the creating "
                      u"groups. <br />The creating group can be preset in scanning program. It's then possible to have "
                      u"multiple scanners and separated 'encoder' groups. "
                      u"The list of 'encoder' groups, can be generated to be used in 'scanner program'."),
        default=False
    )

    model.fieldset(
        'contact',
        label=_(u"Contacts"),
        fields=['all_backrefs_view', 'contact_group_encoder']
    )

    all_backrefs_view = schema.Bool(
        title=_(u'A user can see all mail titles linked to a contact.'),
        default=False
    )

    contact_group_encoder = schema.Bool(
        title=_(u'Activate group encoder'),
        description=_(u"ONCE ACTIVATED, THIS OPTION CAN'T BE EASILY UNDONE !! <br />"
                      u"When activating this option, a group encoder function is added in the configuration, a "
                      u"new field is added to the contact form to choose the creating group and permissions are given "
                      u"to the selected creating group. Contacts are then separately handled following the creating "
                      u"groups. <br />This option can be combined with the mail creating group option."),
        default=False
    )

    model.fieldset(
        'general',
        label=_(u"General config tab"),
        fields=['groups_hidden_in_dashboard_filter', 'users_hidden_in_dashboard_filter']
    )

    groups_hidden_in_dashboard_filter = schema.List(
        title=_(u"Groups hidden in dashboards filter"),
        required=False,
        value_type=schema.Choice(vocabulary=u'imio.dms.mail.TreatingGroupsWithDeactivatedVocabulary'),
    )
    widget('groups_hidden_in_dashboard_filter', OrderedSelectFieldWidget, size=10)

    users_hidden_in_dashboard_filter = schema.List(
        title=_(u"Users hidden in dashboards filter"),
        required=False,
        value_type=schema.Choice(vocabulary=u'imio.dms.mail.AssignedUsersWithDeactivatedVocabulary'),
    )
    widget('users_hidden_in_dashboard_filter', OrderedSelectFieldWidget, size=10)

    @invariant
    def validate_settings(data):
        for dic in data.omail_send_modes:
            if not dic['value'].startswith('email') and not dic['value'].startswith('post'):
                raise Invalid(_(u"Outgoingmail tab: send_modes field must have values starting with 'post' or 'email'"))
        for tab, fld in (('Incoming mail', 'imail_group_encoder'), ('Outgoing mail', 'omail_group_encoder'),
                         ('Contacts', 'contact_group_encoder')):
            rec = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(fld)
            if api.portal.get_registry_record(rec) and not getattr(data, fld):
                raise Invalid(_(u"${tab} tab: unchecking '${field}' setting is not expected !!",
                                mapping={'tab': _(tab), 'field': _('Activate group encoder')}))


class SettingsEditForm(RegistryEditForm):
    """
    Define form logic
    """
    form.extends(RegistryEditForm)
    schema = IImioDmsMailConfig

    def update(self):
        super(SettingsEditForm, self).update()
        # !! groups are updated outside and after updateWidgets
        # we will display unconfigured fields
        filt_groups = {'incomingmail': 'imail_fields', 'outgoingmail': 'omail_fields'}
        for grp in self.groups:
            if grp.__name__ not in filt_groups:
                continue
            wdg = grp.widgets[filt_groups[grp.__name__]]
            def_values = [row['field_name'] for row in wdg.value]
            voc_name = wdg.field.value_type.schema['field_name'].vocabularyName
            voc = getUtility(IVocabularyFactory, voc_name)(self.context)
            unconfigured = ['"{}"'.format(t.title) for t in voc._terms if t.value not in def_values]
            if unconfigured:
                wdg.field = copy.copy(wdg.field)
                wdg.field.description = u'{}<br />{}'.format(
                    _tr(u'Configure this carefully. You can order with arrows.'),
                    _tr(u'<span class="unconfigured-fields">Unconfigured fields are: ${list}</span>',
                        mapping={'list': u', '.join(unconfigured)}))


SettingsView = layout.wrap_form(SettingsEditForm, ControlPanelFormWrapper)


def imiodmsmail_settings_changed(event):
    """ Manage a record change """
    if (IRecordModifiedEvent.providedBy(event) and event.record.interfaceName
            and event.record.interface != IImioDmsMailConfig):
        return
    if event.record.fieldName == 'mail_types':
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.IMMailTypesVocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.IMActiveMailTypesVocabulary')
    if event.record.fieldName == 'omail_types':
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMMailTypesVocabulary')
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.OMActiveMailTypesVocabulary')
    if event.record.fieldName == 'assigned_user_check':
        update_transitions_auc_config('dmsincomingmail')  # i_e ok
        n_plus_x = 'imio.dms.mail.wfadaptations.IMServiceValidation' in \
                   [adapt['adaptation'] for adapt in get_applied_adaptations()]
        snoi = False
        if event.newValue == u'no_check' or not n_plus_x:
            snoi = True
        portal = api.portal.get()
        folder = portal['incoming-mail']['mail-searches']
        if folder['to_treat_in_my_group'].showNumberOfItems != snoi:
            folder['to_treat_in_my_group'].showNumberOfItems = snoi  # noqa
            folder['to_treat_in_my_group'].reindexObject()
    if event.record.fieldName in ('org_templates_encoder_can_edit', 'org_email_templates_encoder_can_edit'):
        folder_id = ('email' in event.record.fieldName) and 'oem' or 'om'
        portal = api.portal.get()
        main_folder = portal.templates[folder_id]
        s_orgs = get_registry_organizations()
        roles = ['Reader']
        all_roles = ['Reader', 'Contributor', 'Editor']
        if api.portal.get_registry_record(event.record.__name__):
            roles = list(all_roles)
        for uid in s_orgs:
            if uid not in main_folder:
                continue
            folder = main_folder[uid]
            groupname = '{}_encodeur'.format(uid)
            api.group.revoke_roles(groupname=groupname, roles=all_roles, obj=folder)
            api.group.grant_roles(groupname=groupname, roles=roles, obj=folder)

    if event.record.fieldName == 'imail_group_encoder':
        if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder'):
            configure_group_encoder(['dmsincomingmail', 'dmsincoming_email'])
    if event.record.fieldName == 'omail_group_encoder':
        if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_group_encoder'):
            # configure_group_encoder(['dmsoutgoingmail', 'dmsoutgoing_email'])
            configure_group_encoder(['dmsoutgoingmail'])
    if event.record.fieldName == 'contact_group_encoder':
        if api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder'):
            configure_group_encoder(['organization', 'person', 'held_position', 'contact_list'], contacts_part=True)
            # set permission on contacts directory
            portal = api.portal.get()
            portal['contacts'].manage_permission('imio.dms.mail: Write mail base fields',
                                                 ('Manager', 'Site Administrator', 'Contributor'), acquire=1)
    if event.record.fieldName == 'groups_hidden_in_dashboard_filter':
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.TreatingGroupsForFacetedFilterVocabulary')
    if event.record.fieldName == 'users_hidden_in_dashboard_filter':
        invalidate_cachekey_volatile_for('imio.dms.mail.vocabularies.AssignedUsersForFacetedFilterVocabulary')


def configure_group_encoder(portal_types, contacts_part=False):
    """
        Used to configure a creating function and group for some internal organizations.
        Update portal_type to add behavior, configure localroles field
    """
    # function
    functions = get_registry_functions()
    if CREATING_GROUP_SUFFIX not in [fct['fct_id'] for fct in functions]:
        functions.append({'fct_title': u'Indicateur du service', 'fct_id': CREATING_GROUP_SUFFIX, 'fct_orgs': [],
                          'fct_management': False, 'enabled': True})
        set_registry_functions(functions)
    if contacts_part and CONTACTS_PART_SUFFIX not in [fct['fct_id'] for fct in functions]:
        functions.append({'fct_title': u'Contacts par défaut', 'fct_id': CONTACTS_PART_SUFFIX, 'fct_orgs': [],
                          'fct_management': False, 'enabled': True})
        set_registry_functions(functions)
    # role and permission
    portal = api.portal.get()
    # existing_roles = list(portal.valid_roles())
    # if CREATING_FIELD_ROLE not in existing_roles:
    #     existing_roles.append(CREATING_FIELD_ROLE)
    #     portal.__ac_roles__ = tuple(existing_roles)
    #     portal.manage_permission('imio.dms.mail: Write creating group field',
    #                              ('Manager', 'Site Administrator', CREATING_FIELD_ROLE), acquire=0)

    # local roles config
    config = {
        'dmsincomingmail': {  # i_e ok
            'created': {CREATING_GROUP_SUFFIX: {'roles': ['Contributor', 'Editor', 'DmsFile Contributor',
                                                          'Base Field Writer', 'Treating Group Writer']}},
            #                                                          CREATING_FIELD_ROLE]}},
            'proposed_to_manager': {CREATING_GROUP_SUFFIX: {'roles': ['Base Field Writer', 'Reader']}},
            'proposed_to_agent': {CREATING_GROUP_SUFFIX: {'roles': ['Reader']}},
            'in_treatment': {CREATING_GROUP_SUFFIX: {'roles': ['Reader']}},
            'closed': {CREATING_GROUP_SUFFIX: {'roles': ['Reader']}}
        },
        'dmsincoming_email': {
            'created': {CREATING_GROUP_SUFFIX: {'roles': ['Contributor', 'Editor', 'DmsFile Contributor',
                                                          'Base Field Writer', 'Treating Group Writer']}},
            #                                                          CREATING_FIELD_ROLE]}},
            'proposed_to_manager': {CREATING_GROUP_SUFFIX: {'roles': ['Base Field Writer', 'Reader']}},
            'proposed_to_agent': {CREATING_GROUP_SUFFIX: {'roles': ['Reader']}},
            'in_treatment': {CREATING_GROUP_SUFFIX: {'roles': ['Reader']}},
            'closed': {CREATING_GROUP_SUFFIX: {'roles': ['Reader']}}
        },
        'dmsoutgoingmail': {
            'to_be_signed': {CREATING_GROUP_SUFFIX: {'roles': ['Editor', 'Reviewer']}},
            'sent': {CREATING_GROUP_SUFFIX: {'roles': ['Reader', 'Reviewer']}},
            'scanned': {CREATING_GROUP_SUFFIX: {'roles': ['Contributor', 'Editor', 'Reviewer', 'DmsFile Contributor',
                                                          'Base Field Writer', 'Treating Group Writer']}},
        },
        # 'dmsoutgoing_email': {
        #     'to_be_signed': {CREATING_GROUP_SUFFIX: {'roles': ['Editor', 'Reviewer']}},
        #     'sent': {CREATING_GROUP_SUFFIX: {'roles': ['Reader', 'Reviewer']}},
        #     'scanned': {CREATING_GROUP_SUFFIX: {'roles': ['Contributor', 'Editor', 'Reviewer', 'DmsFile Contributor',
        #                                                   'Base Field Writer', 'Treating Group Writer']}},
        # },
    }

    # add localroles for possible proposed_to_n_plus_ states
    # only incoming mails
    if 'dmsincomingmail' in portal_types:  # i_e ok
        for typ in ('dmsincomingmail', 'dmsincoming_email'):
            states = list_wf_states(portal, typ)
            for state in states:
                if state.id.startswith('proposed_to_n_plus_'):
                    config[typ][state.id] = {CREATING_GROUP_SUFFIX: {'roles': ['Reader']}}

    # criterias config
    criterias = {
        'dmsincomingmail': ('incoming-mail', 'mail-searches', 'all_mails'),  # i_e ok
        'dmsoutgoingmail': ('outgoing-mail', 'mail-searches', 'all_mails'),
        'organization': ('contacts', 'orgs-searches', 'all_orgs'),
        'person': ('contacts', 'persons-searches', 'all_persons'),
        'held_position': ('contacts', 'hps-searches', 'all_hps'),
        'contact_list': ('contacts', 'cls-searches', 'all_cls'),
    }

    for portal_type in portal_types:
        # behaviors
        fti = getUtility(IDexterityFTI, name=portal_type)
        # try:
        #     fti = getUtility(IDexterityFTI, name=portal_type)
        # except ComponentLookupError:
        #     continue
        if 'imio.dms.mail.content.behaviors.IDmsMailCreatingGroup' not in fti.behaviors:
            old_bav = tuple(fti.behaviors)
            fti.behaviors = tuple(list(fti.behaviors) + ['imio.dms.mail.content.behaviors.IDmsMailCreatingGroup'])
            ftiModified(fti, ObjectModifiedEvent(fti, DexterityFTIModificationDescription('behaviors', old_bav)))

        # local roles
        if config.get(portal_type):
            msg = add_fti_configuration(portal_type, config[portal_type], keyname='creating_group')
            if msg:
                logger.warn(msg)

        # criterias
        folder_id, category_id, default_id = criterias.get(portal_type, ('', '', ''))
        if folder_id:
            reimport_faceted_config(portal[folder_id][category_id], xml='mail-searches-group-encoder.xml',
                                    default_UID=portal[folder_id][category_id][default_id].UID())
