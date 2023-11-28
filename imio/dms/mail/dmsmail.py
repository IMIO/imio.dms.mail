# -*- coding: utf-8 -*-

"""
    This module contains mainly dms types and their view methods.
"""
from AccessControl import ClassSecurityInfo
from AccessControl import getSecurityManager
from AccessControl.class_init import InitializeClass
from collective.contact.core.interfaces import IContactable
from collective.contact.plonegroup.browser.settings import SelectedOrganizationsElephantVocabulary
from collective.contact.plonegroup.utils import get_selected_org_suffix_principal_ids
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.plonegroup.utils import voc_selected_org_suffix_userids
from collective.contact.widget.schema import ContactChoice
from collective.contact.widget.schema import ContactList
from collective.contact.widget.source import ContactSource
from collective.contact.widget.source import ContactSourceBinder
from collective.dms.basecontent.browser.views import DmsDocumentEdit
from collective.dms.basecontent.browser.views import DmsDocumentView
from collective.dms.mailcontent import _ as _cdmsm  # noqa
from collective.dms.mailcontent.browser.views import AddOM as BaseAddOM
from collective.dms.mailcontent.browser.views import OMCustomAddForm as BaseOMAddForm
from collective.dms.mailcontent.browser.views import OMEdit as BaseOMEdit
from collective.dms.mailcontent.dmsmail import DmsIncomingMail
from collective.dms.mailcontent.dmsmail import DmsOutgoingMail
from collective.dms.mailcontent.dmsmail import IDmsIncomingMail
from collective.dms.mailcontent.dmsmail import IDmsOutgoingMail
from collective.dms.mailcontent.dmsmail import IFieldsetOutgoingEmail
from collective.dms.mailcontent.dmsmail import originalMailDateDefaultValue
from collective.task.behaviors import ITask
from collective.task.field import LocalRoleMasterSelectField
from collective.z3cform.select2.widget.widget import SingleSelect2FieldWidget
from datetime import datetime
from datetime import timedelta
from dexterity.localrolesfield.field import LocalRolesField
from imio.dms.mail import _
from imio.dms.mail import AUC_RECORD
from imio.dms.mail import BACK_OR_AGAIN_ICONS
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import OM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import TASK_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail.browser.settings import IImioDmsMailConfig
from imio.dms.mail.browser.task import TaskEdit
from imio.dms.mail.interfaces import IImioDmsIncomingMailWfConditions
from imio.dms.mail.interfaces import IImioDmsOutgoingMailWfConditions
from imio.dms.mail.utils import add_content_in_subfolder
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import do_next_transition
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import is_in_user_groups
from imio.dms.mail.utils import is_n_plus_level_obsolete
from imio.dms.mail.utils import manage_fields
from imio.dms.mail.utils import object_modified_cachekey
from imio.dms.mail.vocabularies import encodeur_active_orgs
# from imio.dms.mail.vocabularies import ServicesSourceBinder
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import object_values
from imio.helpers.content import uuidsToCatalogBrains
from imio.helpers.content import uuidToObject
from imio.helpers.emailer import validate_email_address
from plone import api
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.app.dexterity.behaviors.metadata import IDublinCore
from plone.autoform import directives
# from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.schema import DexteritySchemaPolicy
# from plone.formwidget.autocomplete.widget import AutocompleteMultiFieldWidget
from plone.formwidget.datetime.z3cform.widget import DatetimeFieldWidget
from plone.formwidget.masterselect.widget import MasterSelectJSONValue
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from unidecode import unidecode
from z3c.form import validator
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.interface import implements
from zope.interface import Invalid
from zope.schema import ValidationError
from zope.schema.fieldproperty import FieldProperty
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import copy

now = datetime.today()


def creating_group_filter(context):
    """Catalog criteria vocabulary used in contact search on some Contact fields.

    :param context: the add, edit or view context
    :return: vocabulary containing a criteria dict
    :rtype: SimpleVocabulary or None
    """
    if not api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder'):
        return None
    factory = getUtility(IVocabularyFactory, 'imio.dms.mail.ActiveCreatingGroupVocabulary')
    voc = factory(context)
    # TODO EnhancedTerm ?
    new_term = SimpleTerm(None, token='all', title=_('All'))
    setattr(new_term, '__org__', None)
    terms = [new_term]
    for term in voc:
        # beware to enclose dic content with " to be loaded correctly with json.loads
        new_term = SimpleTerm(u'{{"assigned_group": "{}"}}'.format(term.value), token=term.token, title=term.title)
        setattr(new_term, '__org__', term.value)
        terms.append(new_term)
    return SimpleVocabulary(terms)


alsoProvides(creating_group_filter, IContextSourceBinder)


def creating_group_filter_default(context):
    """Default value of vocabulary returned by creating_group_filter.

    :param context: the add, edit or view context
    :return: term value corresponding to the current user (creating group) organization
    :rtype: unicode or None
    """
    voc = creating_group_filter(context)
    """ Return default value for sender """
    if voc is None:
        return None
    current_user = api.user.get_current()
    if current_user.getId() is None:
        return None
    orgs = organizations_with_suffixes(get_plone_groups_for_user(user=current_user),
                                       [CREATING_GROUP_SUFFIX, CONTACTS_PART_SUFFIX], group_as_str=True)
    for term in voc:
        if term.__org__ in orgs:
            return term.value
    return None


class DmsContactSource(ContactSource):
    """Overrides of ContactSource to set do_post_sort value to False.
    So results aren't sorted by title.
    """

    do_post_sort = False  # do not sort by title before displaying search results (used in contact.widget)

    def __init__(self, context, selectable_filter, navigation_tree_query=None,
                 default=None, defaultFactory=None, **kw):  # noqa
        """Changes sort_on criteria from list to string."""
        super(DmsContactSource, self).__init__(context, selectable_filter, navigation_tree_query,
                                               default, defaultFactory, **kw)
        # criteria cannot be a list. We correct it
        if 'sort_on' in self.selectable_filter.criteria:
            self.selectable_filter.criteria['sort_on'] = self.selectable_filter.criteria['sort_on'][0]


class DmsContactSourceBinder(ContactSourceBinder):

    path_source = DmsContactSource


def filter_dmsincomingmail_assigned_users(org_uid):
    """
        Filter assigned_user in dms incoming mail
    """
    voc = voc_selected_org_suffix_userids(org_uid, IM_EDITOR_SERVICE_FUNCTIONS)
    if len(voc) == 1:
        req = api.env.getRequest()
        view = req.get('PUBLISHED', None)
        if view is None:
            return voc
        elif isinstance(view, MasterSelectJSONValue):
            form = view.widget.form
            if 'ITask.assigned_user' in form.widgets and not form.widgets['ITask.assigned_user'].value:
                view.request.set('_default_assigned_user_', voc.by_value.keys()[0])
    return voc


class IImioDmsIncomingMail(IDmsIncomingMail):
    """
        Extended schema for mail type field
    """

    orig_sender_email = schema.TextLine(
        title=_(u"Original sender email"),
        required=False,
        constraint=validate_email_address,
    )

    sender = ContactList(
        title=_(u'Sender'),
        required=True,
        prefilter_vocabulary=creating_group_filter,
        prefilter_default_value=creating_group_filter_default,
        value_type=ContactChoice(
            source=DmsContactSourceBinder(portal_type=("organization", 'held_position', 'person', 'contact_list'),
                                          review_state=['active'],
                                          sort_on='sortable_title')
        )
    )

    treating_groups = LocalRoleMasterSelectField(
        title=_(u"Treating groups"),
        required=True,
        vocabulary=u'collective.dms.basecontent.treating_groups',
        slave_fields=(
            {'name': 'ITask.assigned_user',
             'slaveID': '#form-widgets-ITask-assigned_user',
             'action': 'vocabulary',
             'vocab_method': filter_dmsincomingmail_assigned_users,
             'control_param': 'org_uid',
             'initial_trigger': True,
             },
        )
    )
    # master select don't work with AjaxChosenFieldWidget widget
    # TODO try when using select2 (DMS-379)
    # directives.widget('treating_groups', AjaxChosenFieldWidget, populate_select=True)
    # Using write_permission hides field. Using display in edit view is preferred
    # directives.write_permission(treating_groups='imio.dms.mail.write_treating_group_field')

    recipient_groups = LocalRolesField(
        title=_(u"Recipient groups"),
        required=False,
        value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups')
        # value_type=schema.Choice(source=ServicesSourceBinder())
    )
#    directives.widget(recipient_groups=AutocompleteMultiFieldWidget)  #22423

    mail_type = schema.Choice(
        title=_("Mail type"),
        # description = _("help_mail_type",
        # default=u"Enter the mail type"),
        required=True,
        vocabulary=u'imio.dms.mail.IMActiveMailTypesVocabulary',
        default=None,
    )

    document_in_service = schema.Bool(
        title=_(u'Original document in service'),
        default=False
    )
    directives.widget(document_in_service=RadioFieldWidget)

    directives.omitted('related_docs', 'recipients', 'notes')
    # directives.widget(recipient_groups=SelectFieldWidget)


# Compatibility with old vocabularies
TreatingGroupsVocabulary = SelectedOrganizationsElephantVocabulary
RecipientGroupsVocabulary = SelectedOrganizationsElephantVocabulary


class ImioDmsIncomingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):  # noqa
        return (IImioDmsIncomingMail, )

# alsoProvides(IImioDmsIncomingMail, IFormFieldProvider) #needed for behavior


class ImioDmsIncomingMail(DmsIncomingMail):
    """
    """
    implements(IImioDmsIncomingMail)
    __ac_local_roles_block__ = True

    treating_groups = FieldProperty(IImioDmsIncomingMail[u'treating_groups'])
    recipient_groups = FieldProperty(IImioDmsIncomingMail[u'recipient_groups'])

    @ram.cache(object_modified_cachekey)
    def IM_get_back_or_again_icon(self):
        return BACK_OR_AGAIN_ICONS[back_or_again_state(self)]

    get_back_or_again_icon = IM_get_back_or_again_icon

    def is_n_plus_level_obsolete(self, treating_group='', state=None, config=None, state_start='proposed_to_n_plus'):
        """Check if current treating_groups has validators on the state"""
        return is_n_plus_level_obsolete(self, 'dmsincomingmail', treating_group=treating_group, state=state,
                                        config=config, state_start=state_start)

    def do_next_transition(self, treating_group='', state=None, config=None):
        """Do next transition following transition_levels"""
        do_next_transition(self, 'dmsincomingmail', treating_group=treating_group, state=state, config=config)

    def wf_conditions(self):
        """Returns the adapter providing workflow conditions"""
        return IImioDmsIncomingMailWfConditions(self)


class ImioDmsIncomingMailWfConditionsAdapter(object):
    implements(IImioDmsIncomingMailWfConditions)
    adapts(IImioDmsIncomingMail)
    security = ClassSecurityInfo()

    def __init__(self, context):
        self.context = context

    security.declarePublic('can_close')

    def can_close(self):
        """Check if idm can be closed.

        A user can close if:
            * a sender, a treating_groups and a mail_type are recorded
            * the closing agent is in the service (an event will set it)

        Used in guard expression for close transition.
        """
        if self.context.sender is None or self.context.treating_groups is None or self.context.mail_type is None:
            # TODO must check if mail_type field is activated. Has a user already modified the object to
            # complete all fields
            return False
        # A user that can be an assigned_user can close. An event will set the value...
        return is_in_user_groups(groups=('dir_general', ), admin=True, suffixes=IM_EDITOR_SERVICE_FUNCTIONS,
                                 org_uid=self.context.treating_groups)

    security.declarePublic('can_do_transition')

    def can_do_transition(self, transition):
        """Check if N+ transitions and "around" transitions can be done, following N+ users and
        assigned_user configuration. Used in guard expression for some transitions.
        :param transition: transition name to do
        :return: bool
        """
        if self.context.treating_groups is None or not self.context.title:
            # print "no tg: False"
            return False
        way_index = transition.startswith('back_to') and 1 or 0
        transition_to_test = transition
        wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus'])  # i_e ok
        if transition in [tr for (st, tr) in wf_from_to['from']]:
            transition_to_test = 'from_states'
        # show only the next valid level
        state = api.content.get_state(self.context)
        transitions_levels = get_dms_config(['transitions_levels', 'dmsincomingmail'])  # i_e ok
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
            transitions_auc = get_dms_config(['transitions_auc', 'dmsincomingmail', transition])  # i_e ok
            if transitions_auc.get(self.context.treating_groups, False):
                # print 'auc ok: True'
                return True
        else:
            return True  # state ok, back ok
        return False

    security.declarePublic('can_treat')

    def can_treat(self):
        """Check if idm can be treated.

        A user can treat if:
            * a title, a sender, a treating_groups and a mail_type are recorded

        Used in guard expression for treat transition.
        """
        if self.context.title is None or self.context.sender is None or self.context.treating_groups is None:
            # TODO add test on modified to see if object has been changed by a user ?!
            return False
        return True


InitializeClass(ImioDmsIncomingMailWfConditionsAdapter)


def updatewidgets_assigned_user_description(the_form):
    """ Set a description if the field must be completed """
    state = api.content.get_state(the_form.context)
    if state in ('proposed_to_agent', 'in_treatment', 'closed'):  # after a data transfer
        return
    treating_group = the_form.context.treating_groups
    transitions_levels = get_dms_config(['transitions_levels', 'dmsincomingmail'])  # i_e ok
    if state in transitions_levels and treating_group in transitions_levels[state]:
        transition = transitions_levels[state][treating_group][0]
        transitions_auc = get_dms_config(['transitions_auc', 'dmsincomingmail'])  # i_e ok
        if transition in transitions_auc and not transitions_auc[transition].get(treating_group, False):
            the_form.widgets['ITask.assigned_user'].field = copy.copy(the_form.widgets['ITask.assigned_user'].field)
            the_form.widgets['ITask.assigned_user'].field.description = _(u'You must select an assigned user '
                                                                          u'before you can propose to an agent !')


def imio_dmsincomingmail_updatefields(the_form):
    """
        Fields update method for add and edit
    """
    if 'original_mail_date' in the_form.fields:
        the_form.fields['original_mail_date'].field = copy.copy(the_form.fields['original_mail_date'].field)
        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if settings.original_mail_date_required:
            the_form.fields['original_mail_date'].field.required = True
        else:
            the_form.fields['original_mail_date'].field.required = False


def imio_dmsincomingmail_updatewidgets(the_form):
    """
        Widgets update method for add and edit
    """
    is_dim = the_form.context.portal_type in ('dmsincomingmail', 'dmsincoming_email')
    current_user = api.user.get_current()
    if not current_user.has_role(['Manager', 'Site Administrator']):
        the_form.widgets['internal_reference_no'].mode = 'hidden'
        # we empty value to bypass validator when creating object
        if not is_dim:
            the_form.widgets['internal_reference_no'].value = ''

    if 'original_mail_date' in the_form.fields:
        if the_form.widgets['original_mail_date'].field.required:
            if the_form.widgets['original_mail_date'].value == ('', '', ''):  # field value is None
                date = originalMailDateDefaultValue(None)
                the_form.widgets['original_mail_date'].value = (date.year, date.month, date.day)
        else:
            # if the context original_mail_date is already set, the widget value is good and must be kept
            if not is_dim or the_form.context.original_mail_date is None:
                the_form.widgets['original_mail_date'].value = ('', '', '')

    if is_dim and the_form.context.treating_groups and the_form.context.assigned_user is None:
        updatewidgets_assigned_user_description(the_form)

    # disable left column
    the_form.request.set('disable_plone.leftcolumn', 1)


class IMEdit(DmsDocumentEdit):
    """
        Edit form redefinition to customize fields.
    """

    def updateFields(self):
        super(IMEdit, self).updateFields()
        manage_fields(self, 'imail_fields', 'edit')
        imio_dmsincomingmail_updatefields(self)
        # sm = getSecurityManager()
        # if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context):
        #    self.fields['treating_groups'].field = copy.copy(self.fields['treating_groups'].field)
        #    self.fields['treating_groups'].field.required = False

    def updateWidgets(self, prefix=None):
        super(IMEdit, self).updateWidgets()
        imio_dmsincomingmail_updatewidgets(self)
        sm = getSecurityManager()
        incomingmail_fti = api.portal.get_tool('portal_types').dmsincomingmail
        behaviors = incomingmail_fti.behaviors
        display_fields = []
        if not sm.checkPermission('imio.dms.mail: Write mail base fields', self.context):
            # for dmsincoming_email, a user can change base fields if this was a manual transfert with
            # automatic transitions applied
            if not getattr(self.context, '_iem_agent', False):
                if IDublinCore.__identifier__ in behaviors:
                    display_fields = [
                        'IDublinCore.title',
                        'IDublinCore.description']
                elif IBasic.__identifier__ in behaviors:
                    display_fields = [
                        'IBasic.title',
                        'IBasic.description']

                display_fields.extend([
                    'sender',
                    'mail_type',
                    'reception_date',
                    'original_mail_date',
                ])

        for field in display_fields:
            if field in self.fields:
                self.widgets[field].mode = 'display'

        if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context) and \
                not getattr(self.context, '_iem_agent', False):
            # cannot do disabled = True because ConstraintNotSatisfied: (True, 'disabled')
            # self.widgets['treating_groups'].__dict__['disabled'] = True
            self.widgets['treating_groups'].terms.terms = SimpleVocabulary(
                [t for t in self.widgets['treating_groups'].terms.terms if t.token == self.context.treating_groups])

        state = api.content.get_state(obj=self.context)

        # Set a due date only if its still created and the value was not set before
        if state == 'created' and 'ITask.due_date' in self.fields and \
                self.widgets['ITask.due_date'].value == ('', '', ''):
            due_date_extension = api.portal.get_registry_record(name='due_date_extension', interface=IImioDmsMailConfig)
            if due_date_extension > 0:
                due_date = datetime.today() + timedelta(days=due_date_extension)
                self.widgets['ITask.due_date'].value = (due_date.year, due_date.month, due_date.day)

        if not self.widgets['orig_sender_email'].value:
            self.widgets['orig_sender_email'].mode = HIDDEN_MODE

    # def applyChanges(self, data):
    #    """ We need to remove a disabled field from data """
    #    sm = getSecurityManager()
    #    if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context):
    #        del data['treating_groups']
    #    super(IMEdit, self).applyChanges(data)


class IMView(DmsDocumentView):
    """
        View form redefinition to customize fields.
    """

    def updateFieldsFromSchemata(self):
        super(IMView, self).updateFieldsFromSchemata()
        manage_fields(self, 'imail_fields', 'view')

    def updateWidgets(self, prefix=None):
        super(IMView, self).updateWidgets()
        # this is added to escape treatment when displaying single widget in column
        # if prefix == 'escape':
        #    return
        if not self.widgets['orig_sender_email'].value:
            self.widgets['orig_sender_email'].mode = HIDDEN_MODE

        if self.context.treating_groups and self.context.assigned_user is None:
            updatewidgets_assigned_user_description(self)


class CustomAddForm(DefaultAddForm):

    portal_type = 'dmsincomingmail'  # i_e ok

    def updateFields(self):
        super(CustomAddForm, self).updateFields()
        manage_fields(self, 'imail_fields', 'edit')
        imio_dmsincomingmail_updatefields(self)

    def updateWidgets(self, prefix=None):
        super(CustomAddForm, self).updateWidgets()
        imio_dmsincomingmail_updatewidgets(self)
        if self.portal_type == 'dmsincomingmail':
            self.widgets['orig_sender_email'].mode = HIDDEN_MODE
        # Set a due date by default if it was set in the configuration
        due_date_extension = api.portal.get_registry_record(name='due_date_extension', interface=IImioDmsMailConfig)
        if due_date_extension > 0:
            due_date = datetime.today() + timedelta(days=due_date_extension)
            self.widgets['ITask.due_date'].value = (due_date.year, due_date.month, due_date.day)

    def add(self, obj):
        container, new_object = add_content_in_subfolder(self, obj, datetime.now())
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        if fti.immediate_view:
            self.immediate_view = "/".join([container.absolute_url(), new_object.id, fti.immediate_view])
        else:
            self.immediate_view = "/".join([container.absolute_url(), new_object.id])


class AddIM(DefaultAddView):

    form = CustomAddForm


class IEMCustomAddForm(CustomAddForm):

    portal_type = 'dmsincoming_email'


class AddIEM(DefaultAddView):

    form = IEMCustomAddForm

###################################################################
#                        OUTGOING MAILS                           #
###################################################################


def filter_dmsoutgoingmail_assigned_users(org_uid):
    """
        Filter assigned_user in dms outgoing mail
        No need to manage '_default_assigned_user_' because assigned_user is here mandatory:
        the first voc value is selected
    """
    # return voc_selected_org_suffix_userids(org_uid, OM_EDITOR_SERVICE_FUNCTIONS, api.user.get_current().getId())
    return voc_selected_org_suffix_userids(org_uid, OM_EDITOR_SERVICE_FUNCTIONS)


def recipients_filter_default(context):
    """ Return default value for recipients """
    voc = creating_group_filter(context)
    if voc is None:
        return None
    current_user = api.user.get_current()
    if current_user.getId() is None:
        return None
    # user can be a real "indicator" or an agent
    orgs = organizations_with_suffixes(get_plone_groups_for_user(user=current_user),
                                       [CREATING_GROUP_SUFFIX, CONTACTS_PART_SUFFIX], group_as_str=True)
    for term in voc:
        if term.__org__ in orgs:
            return term.value
    return None


class IImioDmsOutgoingMail(IDmsOutgoingMail):
    """
        Extended schema for mail type field
    """

    treating_groups = LocalRoleMasterSelectField(
        title=_(u"Treating groups"),
        required=True,
        # vocabulary=u'collective.dms.basecontent.treating_groups',
        source=encodeur_active_orgs,
        slave_fields=(
            {'name': 'ITask.assigned_user',
             'slaveID': '#form-widgets-ITask-assigned_user',
             'action': 'vocabulary',
             'vocab_method': filter_dmsoutgoingmail_assigned_users,
             'control_param': 'org_uid',
             'initial_trigger': True,
             },
        )
    )
    # master select don't work with AjaxChosenFieldWidget widget
    # directives.widget('treating_groups', AjaxChosenFieldWidget, populate_select=True, prompt=False)

    recipient_groups = LocalRolesField(
        title=_(u"Recipient groups"),
        required=False,
        value_type=schema.Choice(vocabulary=u'collective.dms.basecontent.recipient_groups')
    )

    sender = schema.Choice(
        title=_cdmsm(u'Sender'),
        required=True,
        vocabulary=u'imio.dms.mail.OMActiveSenderVocabulary',
    )
    directives.widget('sender', SingleSelect2FieldWidget)

    orig_sender_email = schema.TextLine(
        title=_(u"Original sender email"),
        required=False,
        constraint=validate_email_address,
    )

    recipients = ContactList(
        title=_cdmsm(u'Recipients'),
        required=True,
        value_type=ContactChoice(
            source=DmsContactSourceBinder(portal_type=("organization", 'held_position', 'person', 'contact_list'),
                                          review_state=['active'],
                                          sort_on='sortable_title')),
        prefilter_vocabulary=creating_group_filter,
        prefilter_default_value=recipients_filter_default,
    )

    mail_type = schema.Choice(
        title=_("Mail type"),
        required=True,
        vocabulary=u'imio.dms.mail.OMActiveMailTypesVocabulary',
        default=None,
    )

    send_modes = schema.List(
        title=_("Send modes"),
        value_type=schema.Choice(vocabulary=u'imio.dms.mail.OMActiveSendModesVocabulary'),
        min_length=1,
    )
    directives.widget('send_modes', CheckBoxFieldWidget, multiple='multiple', size=5)

    outgoing_date = schema.Datetime(
        title=_(u'Outgoing Date'),
        required=False,
        min=datetime(1990, 1, 1),
        max=datetime(now.year + 1, 12, 31),)
    directives.widget('outgoing_date', DatetimeFieldWidget, show_today_link=True, show_time=True)

    directives.omitted('related_docs', 'notes')


class ImioDmsOutgoingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):  # noqa
        return IImioDmsOutgoingMail, IFieldsetOutgoingEmail


class ImioDmsOutgoingMail(DmsOutgoingMail):
    """
    """
    implements(IImioDmsOutgoingMail)
    __ac_local_roles_block__ = True

    # Needed by collective.z3cform.rolefield. Need to be overriden here
    treating_groups = FieldProperty(IImioDmsOutgoingMail[u'treating_groups'])
    recipient_groups = FieldProperty(IImioDmsOutgoingMail[u'recipient_groups'])

    def get_mainfiles(self):
        """Overiddes dmsdocument method"""
        return object_values(self, ['ImioDmsFile'])

    def wf_condition_may_set_scanned(self, state_change):  # noqa, pragma: no cover  NO MORE USED
        """ method used in wf condition """
        # python: here.wf_condition_may_set_scanned(state_change)
        user = api.user.get_current()
        if 'expedition' in get_plone_groups_for_user(user=user):
            return True
        roles = api.user.get_roles(user=user)
        if 'Manager' in roles or 'Site Administrator' in roles:
            return True
        return False

    @ram.cache(object_modified_cachekey)
    def OM_get_back_or_again_icon(self):
        return BACK_OR_AGAIN_ICONS[back_or_again_state(self)]

    get_back_or_again_icon = OM_get_back_or_again_icon

    def is_n_plus_level_obsolete(self, treating_group='', state=None, config=None, state_start='proposed_to_n_plus'):
        """Check if current treating_groups has validators on the state"""
        return is_n_plus_level_obsolete(self, 'dmsoutgoingmail', treating_group=treating_group, state=state,
                                        config=config, state_start=state_start)

    def do_next_transition(self, treating_group='', state=None, config=None):
        """Do next transition following transition_levels"""
        do_next_transition(self, 'dmsoutgoingmail', treating_group=treating_group, state=state, config=config)

    def is_email(self):
        """Check if send_modes is related to email.
            :return: boolean
        """
        return bool([val for val in self.send_modes or [] if val.startswith('email')])

    def get_sender_info(self):
        """Returns related sender information:

        * the held_position, in 'hp' key
        * the related person, in 'person' key
        * the related organization, in 'org' key

        :return: dict containing 3 keys
        """
        if not self.sender:
            return {}
        sender = uuidToObject(self.sender, unrestricted=True)
        if not sender:
            return {}
        return {'hp': sender, 'person': sender.get_person(), 'org': sender.get_organization()}

    def get_sender_email(self, sender_i={}):
        """Returns a sender email address

        :param sender_i: a dict containing sender information (as returned by `get_sender_info`)
        :return: an email address
        :rtype: unicode
        """
        if not sender_i:
            sender_i = self.get_sender_info()
        replyto_key = 'imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_sender_email_default'
        rtv = api.portal.get_registry_record(replyto_key, default=u'agent_email')
        if rtv == 'agent_email':
            hpc = IContactable(sender_i['hp'])
            email = hpc.get_contact_details(keys=['email']).get('email', u'')
            if email:
                realname = u"{} {}".format(sender_i['hp'].firstname, sender_i['hp'].lastname)
                return u'"{}" <{}>'.format(unidecode(realname), email)
        elif rtv == 'service_email':
            orgc = IContactable(sender_i['org'])
            email = orgc.get_contact_details(keys=['email']).get('email', u'')
            return email
        return u''

    def get_recipient_emails(self):
        """Returns recipient email addresses

        :return: an email address
        :rtype: unicode
        """
        emails = []
        uniques = []
        if self.orig_sender_email:
            try:
                uniques.append(validate_email_address(self.orig_sender_email)[1])
                emails.append(self.orig_sender_email)
            except ValidationError:
                pass
        # we don't use directly relation object to be sure to use the real object
        uids = [rel.to_object.UID() for rel in self.recipients or []]
        brains = uuidsToCatalogBrains(uids, unrestricted=True)
        # selection order not kept !
        for brain in brains:
            contact = brain._unrestrictedGetObject()
            contactable = IContactable(contact)
            email = contactable.get_contact_details(keys=['email']).get('email', u'')
            if email and email not in uniques:
                uniques.append(email)
                if hasattr(contact, 'firstname'):  # for person or held_position
                    realname = u"{} {}".format(contact.firstname, contact.lastname)
                    emails.append(u'"{}" <{}>'.format(unidecode(realname), email))
                else:
                    emails.append(email)
        return u', '.join(emails)

    def wf_conditions(self):
        """Returns the adapter providing workflow conditions"""
        return IImioDmsOutgoingMailWfConditions(self)


class ImioDmsOutgoingMailWfConditionsAdapter(object):
    implements(IImioDmsOutgoingMailWfConditions)
    adapts(IImioDmsOutgoingMail)
    security = ClassSecurityInfo()

    def __init__(self, context):
        self.context = context

    security.declarePublic('can_be_handsigned')

    def can_be_handsigned(self):
        """Used in guard expression for to_be_signed transitions."""
        brains = self.context.portal_catalog.unrestrictedSearchResults(portal_type='dmsommainfile',
                                                                       path='/'.join(self.context.getPhysicalPath()))
        return bool(brains)

    security.declarePublic('can_be_sent')

    def can_be_sent(self):
        """Used in guard expression for sent transitions."""
        # Protect from scanned state
        if not self.context.treating_groups or not self.context.title:
            return False
        # expedition can always sent
        if is_in_user_groups(['expedition'], admin=True):
            return True
        # email, is sent ?
        if self.context.is_email():
            if self.context.email_status:  # has been sent
                return True
            return False  # consumer will not can "close": ok
        return True

    security.declarePublic('can_be_validated')

    def can_be_validated(self):
        """Used in guard expression for validated transitions."""
        return True

    security.declarePublic('can_back_to_scanned')

    def can_back_to_scanned(self):
        """Used in guard expression for back_to_scanned"""
        if is_in_user_groups(['expedition'], admin=True):
            return True
        return False

    security.declarePublic('can_do_transition')

    def can_do_transition(self, transition):
        """ Used in guard expression for n_plus_1 transitions """
        if self.context.treating_groups is None or not self.context.title:
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


InitializeClass(ImioDmsOutgoingMailWfConditionsAdapter)


def imio_dmsoutgoingmail_updatefields(the_form):
    """
        Fields update method for add, edit and reply !
    """
    the_form.fields['ITask.assigned_user'].field = copy.copy(the_form.fields['ITask.assigned_user'].field)
    the_form.fields['ITask.assigned_user'].field.required = True


def imio_dmsoutgoingmail_updatewidgets(the_form):
    """
        Widgets update method for add, edit and reply !
    """
    # context can be the folder in add or an im in reply.
    if the_form.request.get('masterID'):  # in MS anonymous call, no need to go further
        return

    current_user = api.user.get_current()
    # sender can be None if om is created by worker.
    if (the_form.context.portal_type != 'dmsoutgoingmail' or not the_form.context.sender) and \
            not the_form.widgets['sender'].value:
        # we search for a held position related to current user
        default = treating_group = None
        if the_form.widgets['treating_groups'].value:
            treating_group = the_form.widgets['treating_groups'].value
        else:
            tg_voc = [te for te in the_form.widgets['treating_groups'].terms.terms]
            if tg_voc:
                treating_group = tg_voc[0].value  # primary org can be the first value in vocabulary
        for term in the_form.widgets['sender'].terms:
            if term.token.endswith('_%s' % current_user.id):
                if not default:
                    default = term.token
                if not treating_group:  # not a reply
                    break
                if term.token.endswith('_{}_{}'.format(treating_group, current_user.id)):
                    default = term.token
                    break
        the_form.widgets['sender'].value = [default]

    # disable left column
    the_form.request.set('disable_plone.leftcolumn', 1)


def manage_email_fields(the_form, action):
    """Manages email fieldset following add, edit or view.

    :param the_form: the form
    :param action: 'add', 'edit' or 'view' string
    """
    if action == 'add':
        # we remove email fieldset
        the_form.groups = [gr for gr in the_form.groups if gr.__name__ != 'email']
        return
    if not the_form.context.is_email():
        # we remove email fieldset
        the_form.groups = [gr for gr in the_form.groups if gr.__name__ != 'email']
        return
    if action == 'edit':
        # if '++widget++' in the_form.request.get('URL', ''):
        #    return
        # !! Test on a field value in request must be done in request.form and not in request directly
        # !! to avoid a WrongType email_subject validation (string <-> unicode problem).
        if not (the_form.context.email_subject or 'edit-email' in the_form.request or
                the_form.request.form.get('form.widgets.email_subject')):
            the_form.groups = [gr for gr in the_form.groups if gr.__name__ != 'email']
        return
    if action == 'view' and not the_form.context.email_subject:
        # we remove email fieldset
        the_form.groups = [gr for gr in the_form.groups if gr.__name__ != 'email']
        return


class OMEdit(BaseOMEdit):
    """
        Edit form redefinition to customize fields.
    """

    def update(self):
        super(OMEdit, self).update()
        # !! groups are updated outside and after updateWidgets
        # !! self.groups contains now Group (with widgets) in place of GroupClass
        email_fs = [gr for gr in self.groups if gr.__name__ == 'email']
        if email_fs:
            email_fs = email_fs[0]
            # default values
            subject = email_fs.widgets['email_subject']
            if not subject.value:
                subject.value = self.context.title
            sender = email_fs.widgets['email_sender']
            if not sender.value:
                sender.value = self.context.get_sender_email()
            recipient = email_fs.widgets['email_recipient']
            if not recipient.value:
                recipient.value = self.context.get_recipient_emails()
            # hidden mode
            if 'email_status' in email_fs.widgets:
                email_fs.widgets['email_status'].mode = HIDDEN_MODE
            # email_body signature
            email_body = email_fs.widgets['email_body']
            if not email_body.value:
                res_view = getMultiAdapter((self.context, self.request), name='render_email_signature')
                email_body.value = res_view()

    def updateFields(self):
        super(OMEdit, self).updateFields()
        manage_email_fields(self, 'edit')
        manage_fields(self, 'omail_fields', 'edit')
        imio_dmsoutgoingmail_updatefields(self)

    def updateWidgets(self):
        super(OMEdit, self).updateWidgets()
        imio_dmsoutgoingmail_updatewidgets(self)
        sm = getSecurityManager()
        display_fields = []
        if not sm.checkPermission('imio.dms.mail: Write mail base fields', self.context):
            display_fields = [
                # 'IDublinCore.title',
                # 'IDublinCore.description',
                'sender',
                'recipients',
                'reply_to',
                'external_reference_no',
            ]
        for field in display_fields:
            if field in self.fields:
                self.widgets[field].mode = 'display'

        if not self.widgets['orig_sender_email'].value:
            self.widgets['orig_sender_email'].mode = HIDDEN_MODE

        if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context):
            # cannot do disabled = True because ConstraintNotSatisfied: (True, 'disabled')
            # self.widgets['treating_groups'].__dict__['disabled'] = True
            self.widgets['treating_groups'].terms.terms = SimpleVocabulary(
                [t for t in self.widgets['treating_groups'].terms.terms if t.token == self.context.treating_groups])


class OMCustomAddForm(BaseOMAddForm):

    def updateFields(self):
        super(OMCustomAddForm, self).updateFields()
        manage_email_fields(self, 'add')
        manage_fields(self, 'omail_fields', 'edit')
        imio_dmsoutgoingmail_updatefields(self)

    def updateWidgets(self):
        super(OMCustomAddForm, self).updateWidgets()
        imio_dmsoutgoingmail_updatewidgets(self)
        self.widgets['orig_sender_email'].mode = HIDDEN_MODE
        # a selected value will be reused by masterselect
        self.widgets['ITask.assigned_user'].value = [api.user.get_current().getId()]

    def add(self, obj):
        if not self.request.get('_auto_ref', True):
            setattr(obj, '_auto_ref', False)
        container, new_object = add_content_in_subfolder(self, obj, datetime.now())
        fti = getUtility(IDexterityFTI, name=self.portal_type)
        if fti.immediate_view:
            self.immediate_view = "/".join([container.absolute_url(), new_object.id, fti.immediate_view])
        else:
            self.immediate_view = "/".join([container.absolute_url(), new_object.id])


class AddOM(BaseAddOM):

    form = OMCustomAddForm


class OEMCustomAddForm(OMCustomAddForm):
    portal_type = 'dmsoutgoing_email'


class AddOEM(DefaultAddView):
    form = OEMCustomAddForm


class OMView(DmsDocumentView):
    """
        View form redefinition to customize fields.
    """

    def update(self):
        super(OMView, self).update()
        # !! groups are updated outside and after updateWidgets
        # !! self.groups contains now Group (with widgets) in place of GroupClass
        email_fs = [gr for gr in self.groups if gr.__name__ == 'email']
        if email_fs:
            email_fs = email_fs[0]
            for fldname in email_fs.widgets:
                wdg = email_fs.widgets[fldname]
                if not wdg.value:
                    wdg.mode = HIDDEN_MODE

    def updateFieldsFromSchemata(self):
        super(OMView, self).updateFieldsFromSchemata()
        manage_email_fields(self, 'view')
        manage_fields(self, 'omail_fields', 'view')

    def updateWidgets(self, prefix=None):
        super(OMView, self).updateWidgets()
        if not self.widgets['orig_sender_email'].value:
            self.widgets['orig_sender_email'].mode = HIDDEN_MODE


# Validators

class AssignedUserValidator(validator.SimpleFieldValidator):

    def validate(self, value, force=False):
        config = ((IMEdit, {'attr': 'treating_groups', 'schema': '', 'fcts': IM_EDITOR_SERVICE_FUNCTIONS}),
                  (OMEdit, {'attr': 'treating_groups', 'schema': '', 'fcts': OM_EDITOR_SERVICE_FUNCTIONS}),
                  (TaskEdit, {'attr': 'assigned_group', 'schema': 'ITask.', 'fcts': TASK_EDITOR_SERVICE_FUNCTIONS}),)
        for klass, dic in config:
            if isinstance(self.view, klass):
                # check if group is changed
                form_widget = 'form.widgets.{}{}'.format(dic['schema'], dic['attr'])
                if (getattr(self.context, dic['attr']) is not None and self.request.form.get(form_widget, False) and
                        self.request.form[form_widget][0] != getattr(self.context, dic['attr'])):
                    # check if assigned_user is no more in
                    if (self.context.assigned_user is not None and value is not None and value not in
                            get_selected_org_suffix_principal_ids(self.request.form[form_widget][0], dic['fcts'])):
                        raise Invalid(_(u"The assigned user is not in the selected group !"))
                    # check if assigned_user is needed on dmsincomingmail
                    if klass != IMEdit or value is not None:
                        continue
                    # we are editing an incoming mail and the assigned_user is None
                    # we have to check if the assigned_user must be completed because we will maybe do transitions
                    # in the modified subscriber after the treating_groups modification
                    if api.portal.get_registry_record(AUC_RECORD) != 'mandatory':
                        continue
                    ntg = self.request.form[form_widget][0]
                    doit = True
                    transitions = []
                    state = config = None
                    wf_from_to = get_dms_config(['wf_from_to', 'dmsincomingmail', 'n_plus', 'to'])
                    tr_states = {tup[1]: tup[0] for tup in wf_from_to}
                    while doit:
                        doit, state, config = is_n_plus_level_obsolete(self.context, 'dmsincomingmail',
                                                                       treating_group=ntg, state=state, config=config)
                        if doit:
                            tr = config[state][ntg][0]
                            transitions.append(tr)
                            state = tr_states[tr]
                    if transitions:
                        auc_config = get_dms_config(['transitions_auc', 'dmsincomingmail'])
                        for transition in transitions:
                            if not auc_config[transition].get(ntg, False):
                                raise Invalid(_(u"You must select an assigned user because the treating group "
                                                u"modification to another without validators will cause the mail state "
                                                u"change !"))


validator.WidgetValidatorDiscriminators(AssignedUserValidator, field=ITask['assigned_user'])
