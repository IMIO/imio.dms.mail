# -*- coding: utf-8 -*-


from AccessControl import getSecurityManager
from browser.settings import IImioDmsMailConfig
from collective.contact.plonegroup.browser.settings import SelectedOrganizationsElephantVocabulary
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.contact.plonegroup.utils import voc_selected_org_suffix_users
from collective.contact.widget.schema import ContactChoice
from collective.contact.widget.schema import ContactList
from collective.contact.widget.source import ContactSource
from collective.contact.widget.source import ContactSourceBinder
from collective.dms.basecontent.browser.views import DmsDocumentEdit
from collective.dms.basecontent.browser.views import DmsDocumentView
from collective.dms.mailcontent import _ as _cdmsm
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
from datetime import datetime, timedelta
from dexterity.localrolesfield.field import LocalRolesField
from imio.dms.mail import _
from imio.dms.mail import BACK_OR_AGAIN_ICONS
from imio.dms.mail import DOC_ASSIGNED_USER_FUNCTIONS
from imio.dms.mail.browser.task import TaskEdit
from imio.dms.mail.utils import back_or_again_state
from imio.dms.mail.utils import object_modified_cachekey
#from imio.dms.mail.vocabularies import ServicesSourceBinder
from plone import api
from plone.app.dexterity.behaviors.metadata import IBasic
from plone.app.dexterity.behaviors.metadata import IDublinCore
from plone.autoform import directives
#from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.browser.add import DefaultAddForm
from plone.dexterity.browser.add import DefaultAddView
from plone.dexterity.schema import DexteritySchemaPolicy
#from plone.formwidget.autocomplete.widget import AutocompleteMultiFieldWidget
from plone.formwidget.datetime.z3cform.widget import DatetimeFieldWidget
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from plone.z3cform.fieldsets.utils import move
from Products.CMFPlone.utils import base_hasattr
from vocabularies import encodeur_active_orgs
from z3c.form import validator
from z3c.form.interfaces import HIDDEN_MODE
from zope import schema
from zope.component import getUtility
from zope.interface import implements
from zope.interface import Invalid
from zope.schema.fieldproperty import FieldProperty
from zope.schema.vocabulary import SimpleVocabulary

import copy


class DmsContactSource(ContactSource):

    do_post_sort = False  # do not sort by title before displaying search results

    def __init__(self, context, selectable_filter, navigation_tree_query=None,
                 default=None, defaultFactory=None, **kw):
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
    return voc_selected_org_suffix_users(org_uid, DOC_ASSIGNED_USER_FUNCTIONS)


class IImioDmsIncomingMail(IDmsIncomingMail):
    """
        Extended schema for mail type field
    """

    sender = ContactList(
        title=_(u'Sender'),
        required=True,
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
#        value_type=schema.Choice(source=ServicesSourceBinder())
    )
#    directives.widget(recipient_groups=AutocompleteMultiFieldWidget)  #22423

    mail_type = schema.Choice(
        title=_("Mail type"),
#        description = _("help_mail_type",
#            default=u"Enter the mail type"),
        required=True,
        vocabulary=u'imio.dms.mail.IMActiveMailTypesVocabulary',
        default=None,
    )

    # doesn't work well if IImioDmsIncomingMail is a behavior instead a subclass
    directives.order_before(sender='recipient_groups')
    directives.order_before(mail_type='recipient_groups')
    directives.order_before(original_mail_date='recipient_groups')
    directives.order_before(reception_date='recipient_groups')
    directives.order_before(internal_reference_no='recipient_groups')
    directives.order_before(external_reference_no='recipient_groups')
    directives.order_before(notes='recipient_groups')
    directives.order_before(treating_groups='recipient_groups')
    directives.order_after(reply_to='recipient_groups')

    directives.omitted('related_docs', 'recipients', 'notes')
    #directives.widget(recipient_groups=SelectFieldWidget)

# Compatibility with old vocabularies
TreatingGroupsVocabulary = SelectedOrganizationsElephantVocabulary
RecipientGroupsVocabulary = SelectedOrganizationsElephantVocabulary


class ImioDmsIncomingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IImioDmsIncomingMail, )

#alsoProvides(IImioDmsIncomingMail, IFormFieldProvider) #needed for behavior


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


def ImioDmsIncomingMailUpdateFields(the_form):
    """
        Fields update method for add and edit
    """
    the_form.fields['original_mail_date'].field = copy.copy(the_form.fields['original_mail_date'].field)
    settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
    if settings.original_mail_date_required:
        the_form.fields['original_mail_date'].field.required = True
    else:
        the_form.fields['original_mail_date'].field.required = False


def ImioDmsIncomingMailUpdateWidgets(the_form):
    """
        Widgets update method for add and edit
    """
    current_user = api.user.get_current()
    if not current_user.has_role(['Manager', 'Site Administrator']):
        the_form.widgets['internal_reference_no'].mode = 'hidden'
        # we empty value to bypass validator when creating object
        if the_form.context.portal_type not in ('dmsincomingmail', 'dmsincoming_email'):
            the_form.widgets['internal_reference_no'].value = ''

    for field in ['ITask.assigned_group', 'ITask.enquirer', 'IVersionable.changeNote']:
        the_form.widgets[field].mode = HIDDEN_MODE

    if the_form.widgets['original_mail_date'].field.required:
        if the_form.widgets['original_mail_date'].value == ('', '', ''):  # field value is None
            date = originalMailDateDefaultValue(None)
            the_form.widgets['original_mail_date'].value = (date.year, date.month, date.day)
    else:
        # if the context original_mail_date is already set, the widget value is good and must be kept
        if not base_hasattr(the_form.context, 'original_mail_date') or the_form.context.original_mail_date is None:
            the_form.widgets['original_mail_date'].value = ('', '', '')

    # disable left column
    the_form.request.set('disable_plone.leftcolumn', 1)


class IMEdit(DmsDocumentEdit):
    """
        Edit form redefinition to customize fields.
    """

    def updateFields(self):
        super(IMEdit, self).updateFields()
        ImioDmsIncomingMailUpdateFields(self)
        #sm = getSecurityManager()
        #if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context):
        #    self.fields['treating_groups'].field = copy.copy(self.fields['treating_groups'].field)
        #    self.fields['treating_groups'].field.required = False

    def updateWidgets(self):
        super(IMEdit, self).updateWidgets()
        ImioDmsIncomingMailUpdateWidgets(self)
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
            #self.widgets['treating_groups'].__dict__['disabled'] = True
            self.widgets['treating_groups'].terms.terms = SimpleVocabulary(
                [t for t in self.widgets['treating_groups'].terms.terms if t.token == self.context.treating_groups])

        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        state = api.content.get_state(obj=self.context)
        if settings.assigned_user_check and not self.context.assigned_user \
                and state == 'proposed_to_service_chief':
            self.widgets['ITask.assigned_user'].field = copy.copy(self.widgets['ITask.assigned_user'].field)
            self.widgets['ITask.assigned_user'].field.description = _(u'You must select an assigned user before you'
                                                                      ' can propose to an agent !')

        # Set a due date only if its still created and the value was not set before
        if state == 'created' and self.widgets['ITask.due_date'].value == ('','',''):
            due_date_extension = api.portal.get_registry_record(name='due_date_extension', interface=IImioDmsMailConfig)
            if due_date_extension > 0:
                due_date = datetime.today() + timedelta(days=due_date_extension)
                self.widgets['ITask.due_date'].value = (due_date.year, due_date.month, due_date.day)

    #def applyChanges(self, data):
    #    """ We need to remove a disabled field from data """
    #    sm = getSecurityManager()
    #    if not sm.checkPermission('imio.dms.mail: Write treating group field', self.context):
    #        del data['treating_groups']
    #    super(IMEdit, self).applyChanges(data)


class IMView(DmsDocumentView):
    """
        View form redefinition to customize fields.
    """

    def updateWidgets(self, prefix=None):
        super(IMView, self).updateWidgets()
        # this is added to escape treatment when displaying single widget in column
        #if prefix == 'escape':
        #    return
        for field in ['ITask.assigned_group', 'ITask.enquirer']:
            self.widgets[field].mode = HIDDEN_MODE

        settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
        if settings.assigned_user_check and not self.context.assigned_user \
                and api.content.get_state(obj=self.context) == 'proposed_to_service_chief':
            self.widgets['ITask.assigned_user'].field = copy.copy(self.widgets['ITask.assigned_user'].field)
            self.widgets['ITask.assigned_user'].field.description = _(u'You must select an assigned user before you'
                                                                      ' can propose to an agent !')


class CustomAddForm(DefaultAddForm):

    portal_type = 'dmsincomingmail'

    def updateFields(self):
        super(CustomAddForm, self).updateFields()
        ImioDmsIncomingMailUpdateFields(self)

    def updateWidgets(self):
        super(CustomAddForm, self).updateWidgets()
        ImioDmsIncomingMailUpdateWidgets(self)
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
######                   OUTGOING MAILS                       #####
###################################################################


def filter_dmsoutgoingmail_assigned_users(org_uid):
    """
        Filter assigned_user in dms outgoing mail
    """
    return voc_selected_org_suffix_users(org_uid, DOC_ASSIGNED_USER_FUNCTIONS, api.user.get_current())


class IImioDmsOutgoingMail(IDmsOutgoingMail):
    """
        Extended schema for mail type field
    """

    treating_groups = LocalRoleMasterSelectField(
        title=_(u"Treating groups"),
        required=True,
        #vocabulary=u'collective.dms.basecontent.treating_groups',
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
                                          sort_on='sortable_title')
        )
    )

    mail_type = schema.Choice(
        title=_("Mail type"),
        required=True,
        vocabulary=u'imio.dms.mail.OMActiveMailTypesVocabulary',
        default=None,
    )

    outgoing_date = schema.Datetime(title=_(u'Outgoing Date'), required=False)
    directives.widget('outgoing_date', DatetimeFieldWidget, show_today_link=True, show_time=True)

    directives.order_before(treating_groups='outgoing_date')
    directives.order_before(sender='outgoing_date')
    directives.order_before(recipients='outgoing_date')
    directives.order_before(mail_date='outgoing_date')
    directives.order_before(mail_type='outgoing_date')
    directives.order_before(recipient_groups='outgoing_date')
    directives.order_before(reply_to='outgoing_date')
    directives.order_before(internal_reference_no='outgoing_date')
    directives.order_before(external_reference_no='outgoing_date')
    directives.omitted('related_docs', 'notes')


class ImioDmsOutgoingMailSchemaPolicy(DexteritySchemaPolicy):
    """ """
    def bases(self, schemaName, tree):
        return (IImioDmsOutgoingMail, )


class ImioDmsOutgoingMail(DmsOutgoingMail):
    """
    """
    implements(IImioDmsOutgoingMail)
    __ac_local_roles_block__ = True

    # Needed by collective.z3cform.rolefield. Need to be overriden here
    treating_groups = FieldProperty(IImioDmsOutgoingMail[u'treating_groups'])
    recipient_groups = FieldProperty(IImioDmsOutgoingMail[u'recipient_groups'])

    def wf_condition_may_set_scanned(self, state_change):  # pragma: no cover
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


def ImioDmsOutgoingMailUpdateFields(the_form):
    """
        Fields update method for add, edit and reply !
    """
    the_form.fields['ITask.assigned_user'].field = copy.copy(the_form.fields['ITask.assigned_user'].field)
    the_form.fields['ITask.assigned_user'].field.required = True
    move(the_form, 'assigned_user', after='treating_groups', prefix='ITask')


def ImioDmsOutgoingMailUpdateWidgets(the_form):
    """
        Widgets update method for add, edit and reply !
    """
    # context can be the folder in add or an im in reply.
    current_user = api.user.get_current()

    # sender can be None if om is created by worker.
    if the_form.context.portal_type not in ('dmsoutgoingmail', 'dmsoutgoing_email') \
            or not the_form.context.sender:
        # we search for a held position related to current user and take the first one !
        default = None
        for term in the_form.widgets['sender'].bound_source:
            if term.token.endswith('_%s' % current_user.id):
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
        ImioDmsOutgoingMailUpdateFields(self)

    def updateWidgets(self):
        super(OMEdit, self).updateWidgets()
        ImioDmsOutgoingMailUpdateWidgets(self)
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
            #self.widgets['treating_groups'].__dict__['disabled'] = True
            self.widgets['treating_groups'].terms.terms = SimpleVocabulary(
                [t for t in self.widgets['treating_groups'].terms.terms if t.token == self.context.treating_groups])


class OMCustomAddForm(BaseOMAddForm):

    def updateFields(self):
        super(OMCustomAddForm, self).updateFields()
        ImioDmsOutgoingMailUpdateFields(self)

    def updateWidgets(self):
        super(OMCustomAddForm, self).updateWidgets()
        ImioDmsOutgoingMailUpdateWidgets(self)
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
        move(self, 'assigned_user', after='treating_groups', prefix='ITask')

    def updateWidgets(self, prefix=None):
        super(OMView, self).updateWidgets()

        for field in ['ITask.assigned_group', 'ITask.enquirer']:
            self.widgets[field].mode = HIDDEN_MODE

# Validators


class AssignedUserValidator(validator.SimpleFieldValidator):

    def validate(self, value):
        # we go out if assigned user is empty
        if value is None:
            return
        # check if we are editing dmsincomingmail or dmsoutgoingmail
        if isinstance(self.view, IMEdit) or isinstance(self.view, IMEdit):
            # check if treating_groups is changed and assigned_user is no more in
            if (self.context.treating_groups is not None and self.context.assigned_user is not None and
                self.request.form['form.widgets.treating_groups'] and
                self.request.form['form.widgets.treating_groups'][0] != self.context.treating_groups and
                value not in [mb.getUserName() for mb in get_selected_org_suffix_users(
                              self.request.form['form.widgets.treating_groups'][0],
                              DOC_ASSIGNED_USER_FUNCTIONS)]):
                    raise Invalid(_(u"The assigned user is not in the selected treating group !"))
        # check if we are editing a task
        elif isinstance(self.view, TaskEdit):
            # check if assigned_group is changed and assigned_user is no more in
            if (self.context.assigned_group is not None and self.context.assigned_user is not None and
                self.request.form['form.widgets.ITask.assigned_group'] and
                self.request.form['form.widgets.ITask.assigned_group'][0] != self.context.assigned_group and
                value not in [mb.getUserName() for mb in get_selected_org_suffix_users(
                              self.request.form['form.widgets.ITask.assigned_group'][0],
                              DOC_ASSIGNED_USER_FUNCTIONS)]):
                    raise Invalid(_(u"The assigned user is not in the selected assigned group !"))

validator.WidgetValidatorDiscriminators(AssignedUserValidator, field=ITask['assigned_user'])
