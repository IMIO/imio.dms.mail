# -*- coding: utf-8 -*-

from AccessControl import getSecurityManager
from browser.settings import IImioDmsMailConfig
from collective.contact.plonegroup.browser.settings import SelectedOrganizationsElephantVocabulary
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.contact.plonegroup.utils import voc_selected_org_suffix_users
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
from collective.dms.mailcontent.dmsmail import originalMailDateDefaultValue
from collective.task.behaviors import ITask
from collective.task.field import LocalRoleMasterSelectField
from collective.z3cform.chosen.widget import AjaxChosenFieldWidget
from datetime import datetime
from datetime import timedelta
from dexterity.localrolesfield.field import LocalRolesField
from imio.dms.mail import _
from imio.dms.mail import BACK_OR_AGAIN_ICONS
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import OM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import TASK_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail.browser.task import TaskEdit
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import object_modified_cachekey
# from imio.dms.mail.vocabularies import ServicesSourceBinder
from plone import api
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.app.dexterity.behaviors.metadata import IDublinCore
from plone.autoform import directives
# from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.schema import DexteritySchemaPolicy
# from plone.formwidget.autocomplete.widget import AutocompleteMultiFieldWidget
from plone.formwidget.datetime.z3cform.widget import DatetimeFieldWidget
from plone.formwidget.masterselect.widget import MasterSelectJSONValue
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from plone.z3cform.fieldsets.utils import add
from plone.z3cform.fieldsets.utils import remove
from vocabularies import encodeur_active_orgs
from z3c.form import validator
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.interface import implements
from zope.interface import Invalid
from zope.schema.fieldproperty import FieldProperty
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import copy


def creating_group_filter(context):
    """ Return catalog criteria vocabulary to add in contact search """
    if not api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder'):
        return None
    factory = getUtility(IVocabularyFactory, 'imio.dms.mail.ActiveCreatingGroupVocabulary')
    voc = factory(context)
    terms = []
    for term in voc:
        # beware to enclose dic content with " to be loaded correctly with json.loads
        new_term = SimpleTerm(u'{{"assigned_group": "{}"}}'.format(term.value), token=term.token, title=term.title)
        setattr(new_term, '__org__', term.value)
        terms.append(new_term)
    return SimpleVocabulary(terms)


alsoProvides(creating_group_filter, IContextSourceBinder)


def creating_group_filter_default(context):
    """ Return default value for sender """
    voc = creating_group_filter(context)
    if voc is None:
        return None
    current_user = api.user.get_current()
    if current_user.getId() is None:
        return None
    orgs = organizations_with_suffixes(api.group.get_groups(user=current_user), [CREATING_GROUP_SUFFIX])
    for term in voc:
        if term.__org__ in orgs:
            return term.value
    return None


class DmsContactSource(ContactSource):

    do_post_sort = False  # do not sort by title before displaying search results (used in contact.widget)

    def __init__(self, context, selectable_filter, navigation_tree_query=None,
                 default=None, defaultFactory=None, **kw):  # noqa
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
    voc = voc_selected_org_suffix_users(org_uid, IM_EDITOR_SERVICE_FUNCTIONS)
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
    def get_back_or_again_icon(self):
        return BACK_OR_AGAIN_ICONS[back_or_again_state(self)]


def order_fields(the_form, config_key):
    """
        Reorder fields
    """
    ordered = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.{}'.format(config_key))
    for field_name in reversed(ordered):
        field = remove(the_form, field_name)
        if field is not None:
            add(the_form, field, index=0)


def updatewidgets_assigned_user_description(the_form):
    """ Set a description if the field must be completed """
    state = api.content.get_state(the_form.context)
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

    for field in ['ITask.assigned_group', 'ITask.enquirer', 'IVersionable.changeNote']:
        the_form.widgets[field].mode = HIDDEN_MODE

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
        order_fields(self, 'imail_fields_order')
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
            self.widgets[field].mode = 'display'

        if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context):
            # cannot do disabled = True because ConstraintNotSatisfied: (True, 'disabled')
            # self.widgets['treating_groups'].__dict__['disabled'] = True
            self.widgets['treating_groups'].terms.terms = SimpleVocabulary(
                [t for t in self.widgets['treating_groups'].terms.terms if t.token == self.context.treating_groups])

        state = api.content.get_state(obj=self.context)

        # Set a due date only if its still created and the value was not set before
        if state == 'created' and self.widgets['ITask.due_date'].value == ('', '', ''):
            due_date_extension = api.portal.get_registry_record(name='due_date_extension', interface=IImioDmsMailConfig)
            if due_date_extension > 0:
                due_date = datetime.today() + timedelta(days=due_date_extension)
                self.widgets['ITask.due_date'].value = (due_date.year, due_date.month, due_date.day)

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
        order_fields(self, 'imail_fields_order')

    def updateWidgets(self, prefix=None):
        super(IMView, self).updateWidgets()
        # this is added to escape treatment when displaying single widget in column
        # if prefix == 'escape':
        #    return
        for field in ['ITask.assigned_group', 'ITask.enquirer']:
            self.widgets[field].mode = HIDDEN_MODE

        if self.context.treating_groups and self.context.assigned_user is None:
            updatewidgets_assigned_user_description(self)


class CustomAddForm(DefaultAddForm):

    portal_type = 'dmsincomingmail'  # i_e ok

    def updateFields(self):
        super(CustomAddForm, self).updateFields()
        order_fields(self, 'imail_fields_order')
        imio_dmsincomingmail_updatefields(self)

    def updateWidgets(self, prefix=None):
        super(CustomAddForm, self).updateWidgets()
        imio_dmsincomingmail_updatewidgets(self)
        # Set a due date by default if it was set in the configuration
        due_date_extension = api.portal.get_registry_record(name='due_date_extension', interface=IImioDmsMailConfig)
        if due_date_extension > 0:
            due_date = datetime.today() + timedelta(days=due_date_extension)
            self.widgets['ITask.due_date'].value = (due_date.year, due_date.month, due_date.day)


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
    return voc_selected_org_suffix_users(org_uid, OM_EDITOR_SERVICE_FUNCTIONS, api.user.get_current())


def recipients_filter_default(context):
    """ Return default value for recipients """
    voc = creating_group_filter(context)
    if voc is None:
        return None
    current_user = api.user.get_current()
    if current_user.getId() is None:
        return None
    # user can be a real "indicator" or an agent
    orgs = organizations_with_suffixes(api.group.get_groups(user=current_user), [CREATING_GROUP_SUFFIX,
                                                                                 CONTACTS_PART_SUFFIX])
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
        vocabulary=u'imio.dms.mail.OMSenderVocabulary',
    )
    directives.widget('sender', AjaxChosenFieldWidget, populate_select=True)

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

    outgoing_date = schema.Datetime(title=_(u'Outgoing Date'), required=False)
    directives.widget('outgoing_date', DatetimeFieldWidget, show_today_link=True, show_time=True)

    directives.omitted('related_docs', 'notes')


class ImioDmsOutgoingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):  # noqa
        return (IImioDmsOutgoingMail, )


class ImioDmsOutgoingMail(DmsOutgoingMail):
    """
    """
    implements(IImioDmsOutgoingMail)
    __ac_local_roles_block__ = True

    # Needed by collective.z3cform.rolefield. Need to be overriden here
    treating_groups = FieldProperty(IImioDmsOutgoingMail[u'treating_groups'])
    recipient_groups = FieldProperty(IImioDmsOutgoingMail[u'recipient_groups'])

    def wf_condition_may_set_scanned(self, state_change):  # noqa, pragma: no cover
        """ method used in wf condition """
        # python: here.wf_condition_may_set_scanned(state_change)
        user = api.user.get_current()
        if 'expedition' in [g.id for g in api.group.get_groups(user=user)]:
            return True
        roles = api.user.get_roles(user=user)
        if 'Manager' in roles or 'Site Administrator' in roles:
            return True
        return False

    @ram.cache(object_modified_cachekey)
    def get_back_or_again_icon(self):
        return BACK_OR_AGAIN_ICONS[back_or_again_state(self)]


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
    current_user = api.user.get_current()

    # sender can be None if om is created by worker.
    if the_form.context.portal_type not in ('dmsoutgoingmail', 'dmsoutgoing_email') \
            or not the_form.context.sender:
        # we search for a held position related to current user and take the first one !
        default = treating_group = None
        if the_form.__name__ == 'reply':
            treating_group = the_form.widgets['treating_groups'].value
        for term in the_form.widgets['sender'].bound_source:
            if term.token.endswith('_%s' % current_user.id):
                if not default:
                    default = term.token
                if not treating_group:  # not a reply
                    break
                if term.token == '{}_{}'.format(treating_group, current_user.id):
                    default = term.token
                    break
        the_form.widgets['sender'].value = [default]

    for field in ['ITask.assigned_group', 'ITask.enquirer', 'IVersionable.changeNote']:
        the_form.widgets[field].mode = HIDDEN_MODE

    # disable left column
    the_form.request.set('disable_plone.leftcolumn', 1)


class OMEdit(BaseOMEdit):
    """
        Edit form redefinition to customize fields.
    """

    def updateFields(self):
        super(OMEdit, self).updateFields()
        order_fields(self, 'omail_fields_order')
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
            self.widgets[field].mode = 'display'

        if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context):
            # cannot do disabled = True because ConstraintNotSatisfied: (True, 'disabled')
            # self.widgets['treating_groups'].__dict__['disabled'] = True
            self.widgets['treating_groups'].terms.terms = SimpleVocabulary(
                [t for t in self.widgets['treating_groups'].terms.terms if t.token == self.context.treating_groups])


class OMCustomAddForm(BaseOMAddForm):

    def updateFields(self):
        super(OMCustomAddForm, self).updateFields()
        order_fields(self, 'omail_fields_order')
        imio_dmsoutgoingmail_updatefields(self)

    def updateWidgets(self):
        super(OMCustomAddForm, self).updateWidgets()
        imio_dmsoutgoingmail_updatewidgets(self)
        # the following doesn't work
        # self.widgets['ITask.assigned_user'].value = [api.user.get_current().getId()]


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

    def updateFieldsFromSchemata(self):
        super(OMView, self).updateFieldsFromSchemata()
        order_fields(self, 'omail_fields_order')

    def updateWidgets(self, prefix=None):
        super(OMView, self).updateWidgets()

        for field in ['ITask.assigned_group', 'ITask.enquirer']:
            self.widgets[field].mode = HIDDEN_MODE

# Validators


class AssignedUserValidator(validator.SimpleFieldValidator):

    def validate(self, value, force=False):
        # we go out if assigned user is empty
        if value is None:
            return
        config = ((IMEdit, {'attr': 'treating_groups', 'schema': '', 'fcts': IM_EDITOR_SERVICE_FUNCTIONS}),
                  (OMEdit, {'attr': 'treating_groups', 'schema': '', 'fcts': OM_EDITOR_SERVICE_FUNCTIONS}),
                  (TaskEdit, {'attr': 'assigned_group', 'schema': 'ITask.', 'fcts': TASK_EDITOR_SERVICE_FUNCTIONS}),)
        for klass, dic in config:
            if isinstance(self.view, klass):
                # check if group is changed and assigned_user is no more in
                form_widget = 'form.widgets.{}{}'.format(dic['schema'], dic['attr'])
                if (getattr(self.context, dic['attr']) is not None and self.context.assigned_user is not None and
                    self.request.form.get(form_widget, False) and
                    self.request.form[form_widget][0] != getattr(self.context, dic['attr']) and
                    value not in [mb.getUserName() for mb in get_selected_org_suffix_users(
                                  self.request.form[form_widget][0], dic['fcts'])]):
                    raise Invalid(_(u"The assigned user is not in the selected group !"))


validator.WidgetValidatorDiscriminators(AssignedUserValidator, field=ITask['assigned_user'])
