# -*- coding: utf-8 -*-
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.config import set_registry_functions
from collective.contact.plonegroup.utils import get_selected_org_suffix_principal_ids
from collective.wfadaptations.api import get_applied_adaptations
from collective.z3cform.datagridfield import DataGridFieldFactory
from collective.z3cform.datagridfield.registry import DictRow
from dexterity.localroles.utils import add_fti_configuration
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import GE_CONFIG
from imio.dms.mail import IM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import MAIN_FOLDERS
from imio.dms.mail.content.behaviors import default_creating_group
from imio.dms.mail.utils import ensure_set_field
from imio.dms.mail.utils import is_valid_identifier
from imio.dms.mail.utils import list_wf_states
from imio.dms.mail.utils import reimport_faceted_config
from imio.dms.mail.utils import update_transitions_auc_config
from imio.dms.mail.utils import vocabularyname_to_terms
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
from plone.registry.recordsproxy import RecordsProxy
from plone.supermodel import model
from plone.z3cform import layout
from Products.CMFPlone.utils import safe_unicode
from z3c.form import form
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.browser.orderedselect import OrderedSelectFieldWidget
# from z3c.form.browser.radio import RadioFieldWidget
# from z3c.form.interfaces import WidgetActionExecutionError
from z3c.form.validator import NoInputData
from zope import schema
from zope.component import getUtility
# from zope.interface import provider
# from zope.schema.interfaces import IContextSourceBinder
from zope.interface import implements
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import invariant
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import copy
import logging
import re


logger = logging.getLogger("imio.dms.mail: settings")


def get_pt_fields_voc(pt, excluded):
    terms = []
    for name, field in get_schema_fields(type_name=pt, prefix=True):
        if name in excluded:
            continue
        terms.append(SimpleTerm(name, title=_tr(field.title)))
    return SimpleVocabulary(humansorted(terms, key=attrgetter("title")))


# @provider(IContextSourceBinder)
# def IMFields(context):
class IMFieldsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return get_pt_fields_voc(
            "dmsincomingmail",  # i_e ok
            [
                "IDublinCore.contributors",
                "IDublinCore.creators",
                "IDublinCore.effective",
                "IDublinCore.expires",
                "IDublinCore.language",
                "IDublinCore.rights",
                "IDublinCore.subjects",
                "INameFromTitle.title",
                "ITask.assigned_group",
                "ITask.enquirer",
                "IVersionable.changeNote",
                "notes",
                "recipients",
                "related_docs",
            ],
        )


class OMFieldsVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return get_pt_fields_voc(
            "dmsoutgoingmail",
            [
                "IDublinCore.contributors",
                "IDublinCore.creators",
                "IDublinCore.effective",
                "IDublinCore.expires",
                "IDublinCore.language",
                "IDublinCore.rights",
                "IDublinCore.subjects",
                "INameFromTitle.title",
                "ITask.assigned_group",
                "ITask.enquirer",
                "IVersionable.changeNote",
                "notes",
                "related_docs",
            ],
        )


class IIMFieldsSchema(Interface):
    field_name = schema.Choice(
        title=_(u"Field name"),
        vocabulary=u"imio.dms.mail.IMFieldsVocabulary",
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
        title=_(u"Field name"),
        vocabulary=u"imio.dms.mail.OMFieldsVocabulary",
    )

    read_tal_condition = schema.TextLine(
        title=_("Read TAL condition"),
        required=False,
    )

    write_tal_condition = schema.TextLine(
        title=_("Write TAL condition"),
        required=False,
    )


routing_forward_types = SimpleVocabulary(
    [
        SimpleTerm(value=u"agent", title=_(u"Agent")),
        SimpleTerm(value=u"server", title=_(u"Server")),
    ]
)


class UsersRoutingValueVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return SimpleVocabulary(
            [
                SimpleTerm(value=None, title=_("Choose a value !")),
                SimpleTerm(value=u"_empty_", title=_("Set None")),
                SimpleTerm(value=u"_transferer_", title=_("Transferer")),
            ] + vocabularyname_to_terms("imio.helpers.SimplySortedUsers", sort_on="title")
        )


class TgRoutingValueVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return SimpleVocabulary(
            [
                SimpleTerm(value=None, title=_("Choose a value !")),
                SimpleTerm(value=u"_empty_", title=_("Set None")),
                SimpleTerm(value=u"_uni_org_only_", title=_("Uniorg only")),
                SimpleTerm(value=u"_primary_org_", title=_("From primary organization")),
                SimpleTerm(value=u"_hp_", title=_("Following held position")),
            ] + vocabularyname_to_terms("collective.dms.basecontent.treating_groups", sort_on="title")
        )


class StatesRoutingValueVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        return SimpleVocabulary(
            [
                SimpleTerm(value=None, title=_("Choose a value !")),
                SimpleTerm(value=u"_n_plus_h_", title=_(u"Highest N+ level, or agent")),
                SimpleTerm(value=u"_n_plus_l_", title=_(u"Lowest N+ level, or agent")),
            ] + vocabularyname_to_terms("imio.dms.mail.IMReviewStatesVocabulary")
        )


class IRuleSchema(Interface):

    forward = schema.Choice(
        title=_("Forward Type"),
        # description=_("Choose between Agent or Server"),
        vocabulary=routing_forward_types,
        required=True
    )

    transfer_email_pat = schema.TextLine(
        title=_(u"Transfer email pattern"),
        description=_(u"Enter a regex pattern"),
        required=False,
    )

    original_email_pat = schema.TextLine(
        title=_(u"Original email pattern"),
        description=_(u"Enter a regex pattern"),
        required=False,
    )

    tal_condition_1 = schema.TextLine(
        title=_("TAL condition 1"),
        required=False,
        default=u"",
    )


class IRoutingSchema(IRuleSchema):

    user_value = schema.Choice(
        title=_(u"Assigned user value"),
        vocabulary="imio.dms.mail.UsersRoutingValueVocabulary",
        required=True,
    )

    tal_condition_2 = schema.TextLine(
        title=_("TAL condition 2"),
        required=False,
        default=u"",
    )

    tg_value = schema.Choice(
        title=_(u"Treating group value"),
        vocabulary="imio.dms.mail.TgRoutingValueVocabulary",
        required=True,
    )


class IStateSetSchema(IRuleSchema):

    state_value = schema.Choice(
        title=_(u"State value"),
        vocabulary="imio.dms.mail.StatesRoutingValueVocabulary",
        required=True,
    )


assigned_user_check_levels = SimpleVocabulary(
    [
        SimpleTerm(value=u"no_check", title=_(u"No check")),
        SimpleTerm(value=u"n_plus_1", title=_(u"Assigned user mandatory only if there is a n+1 validation")),
        SimpleTerm(value=u"mandatory", title=_(u"Assigned user always mandatory")),
    ]
)

fullname_forms = SimpleVocabulary(
    [
        SimpleTerm(value=u"firstname", title=_(u"Firstname Lastname")),
        SimpleTerm(value=u"lastname", title=_(u"Lastname Firstname")),
    ]
)

# iemail_manual_forward_transitions = SimpleVocabulary(
#     [
#         SimpleTerm(value=u"created", title=_(u"A user forwarded email will stay at creation level")),
#         SimpleTerm(value=u"manager", title=_(u"A user forwarded email will go to manager level")),
#         SimpleTerm(
#             value=u"n_plus_h", title=_(u"A user forwarded email will go to highest N+ level, otherwise to agent")
#         ),
#         SimpleTerm(
#             value=u"n_plus_l", title=_(u"A user forwarded email will go to lowest N+ level, otherwise to agent")
#         ),
#         SimpleTerm(value=u"agent", title=_(u"A user forwarded email will go to agent level")),
#     ]
# )

oemail_sender_email_values = SimpleVocabulary(
    [
        SimpleTerm(value=u"agent_email", title=_(u"Sender held position email is used")),
        SimpleTerm(value=u"service_email", title=_(u"Sender held position service email is used")),
    ]
)

oemail_bcc_email_values = SimpleVocabulary(
    [
        SimpleTerm(value=u"agent_email", title=_(u"Sender held position email is used")),
        SimpleTerm(value=u"service_email", title=_(u"Sender held position service email is used")),
    ]
)


class ITableListSchema(Interface):
    value = schema.TextLine(title=_("Stored value/id"), required=True, constraint=is_valid_identifier)
    dtitle = schema.TextLine(title=_("Displayed title"), required=True)
    active = schema.Bool(title=_("Active"), required=False)


class IImioDmsMailConfig(model.Schema):
    """
    Configuration of dms mail
    """

    model.fieldset(
        "incomingmail",
        label=_(u"Incoming mail"),
        fields=[
            "mail_types",
            "assigned_user_check",
            "original_mail_date_required",
            "due_date_extension",
            "imail_remark_states",
            "imail_fields",
            "imail_group_encoder",
        ],
    )

    mail_types = schema.List(
        title=_(u"Types of incoming mail"),
        description=_(
            u"Once created and used, value doesn't be changed anymore. None can be used for a 'choose' value."
        ),
        value_type=DictRow(title=_("Mail type"), schema=ITableListSchema),
    )

    widget("mail_types", DataGridFieldFactory, allow_reorder=True)

    assigned_user_check = schema.Choice(
        title=_(u"Assigned user check"),
        description=_(u"Check if there is an assigned user before proposing incoming mail to an agent."),
        vocabulary=assigned_user_check_levels,
        default=u"n_plus_1",
    )

    original_mail_date_required = schema.Bool(
        title=_(u"Original mail date requirement"),
        description=_(u"Check if the incoming mail 'original mail date' field must be required."),
        default=True,
    )

    due_date_extension = schema.Int(
        title=_(u"Due date extension"),
        description=_(u"Extends the due date by a number of days. 0 means no due date will be set by default."),
        default=0,
        min=0,
    )

    imail_remark_states = schema.List(
        title=_(u"States for which to display remark icon"),
        value_type=schema.Choice(vocabulary=u"imio.dms.mail.IMReviewStatesVocabulary"),
    )

    imail_fields = schema.List(
        title=_(u"${type} fields display", mapping={"type": _("Incoming mail")}),
        description=_(u"Configure this carefully. You can order with arrows."),
        required=False,
        value_type=DictRow(title=_(u"Field"), schema=IIMFieldsSchema, required=False),
    )
    widget(
        "imail_fields",
        DataGridFieldFactory,
        display_table_css_class="listing",
        allow_reorder=True,
        auto_append=False,
    )

    imail_group_encoder = schema.Bool(
        title=_(u"Activate group encoder"),
        description=_(
            u"ONCE ACTIVATED, THIS OPTION CAN'T BE EASILY UNDONE !! <br />"
            u"When activating this option, a group encoder function is added in the configuration, "
            u"a new field is added to the mail form to choose the creating group and permissions are given "
            u"to the selected creating group. Mails are then separately handled following the creating "
            u"groups. <br />The creating group can be preset in scanning program. It's then possible to have "
            u"multiple scanners and separated 'encoder' groups. "
            u"The list of 'encoder' groups, can be generated to be used in 'scanner program'."
        ),
        default=False,
    )

    # FIELDSET IEM
    model.fieldset(
        "incoming_email",
        label=_(u"Incoming email"),
        fields=["iemail_routing", "iemail_state_set"],)

    # iemail_manual_forward_transition = schema.Choice(
    #     title=_(u"Email manual forward transition"),
    #     description=_(u"Choose to which state a manually forwarded email will go."),
    #     vocabulary=iemail_manual_forward_transitions,
    #     default=u"agent",
    # )
    #
    iemail_routing = schema.List(
        title=_(u"${type} routing", mapping={"type": _("Incoming email")}),
        description=_(u"Configure rules carefully. You can order with arrows. Only first matched rule is used."),
        required=False,
        value_type=DictRow(title=_(u"Routing"), schema=IRoutingSchema, required=False),
    )
    widget(
        "iemail_routing",
        DataGridFieldFactory,
        allow_reorder=True,
        auto_append=False,
    )

    iemail_state_set = schema.List(
        title=_(u"${type} state set", mapping={"type": _("Incoming email")}),
        description=_(u"Configure rules carefully. You can order with arrows. Only first matched rule is used."),
        required=False,
        value_type=DictRow(title=_(u"State"), schema=IStateSetSchema, required=False),
    )
    widget(
        "iemail_state_set",
        DataGridFieldFactory,
        allow_reorder=True,
        auto_append=False,
    )

    # FIELDSET OM
    model.fieldset(
        "outgoingmail",
        label=_(u"Outgoing mail"),
        fields=[
            "omail_types",
            "omail_remark_states",
            "omail_response_prefix",
            "omail_odt_mainfile",
            "omail_sender_firstname_sorting",
            "org_templates_encoder_can_edit",
            "omail_fullname_used_form",
            "omail_send_modes",
            "omail_post_mailing",
            "omail_fields",
            "omail_group_encoder",
        ],
    )

    omail_types = schema.List(
        title=_(u"Types of outgoing mail"),
        description=_(
            u"Once created and used, value doesn't be changed anymore. None can be used for a 'choose' value."
        ),
        value_type=DictRow(title=_("Mail type"), schema=ITableListSchema),
    )

    widget("omail_types", DataGridFieldFactory, allow_reorder=True)

    omail_remark_states = schema.List(
        title=_(u"States for which to display remark icon"),
        value_type=schema.Choice(vocabulary=u"imio.dms.mail.OMReviewStatesVocabulary"),
    )

    omail_response_prefix = schema.TextLine(title=_("Response prefix"), required=False)

    omail_odt_mainfile = schema.Bool(title=_(u"Dms file must be an odt format"), default=True)

    omail_sender_firstname_sorting = schema.Bool(title=_(u"Sender list is sorted on firstname"), default=True)

    org_templates_encoder_can_edit = schema.Bool(
        title=_(u"Enable edition of service office templates for encoder"),
        description=_(u"Check if a service encoder can edit his service office templates."),
        default=True,
    )

    omail_fullname_used_form = schema.Choice(
        title=_(u"User fullname used format"),
        vocabulary=fullname_forms,
        default="firstname",
    )

    omail_send_modes = schema.List(
        title=_(u"Send modes"),
        description=_(
            u"Once created and used, value doesn't be changed anymore. None can be used for a 'choose' value."
        ),
        value_type=DictRow(title=_("Send modes"), schema=ITableListSchema),
    )

    widget("omail_send_modes", DataGridFieldFactory, allow_reorder=True)

    omail_post_mailing = schema.Bool(
        title=_(u"Post mailing"),
        description=_(u"Do mailing for each postal sending type."),
        default=False,
    )

    omail_fields = schema.List(
        title=_(u"${type} fields display", mapping={"type": _("Outgoing mail")}),
        description=_(u"Configure this carefully. You can order with arrows."),
        required=False,
        value_type=DictRow(title=_(u"Field"), schema=IOMFieldsSchema, required=False),
    )
    widget(
        "omail_fields",
        DataGridFieldFactory,
        display_table_css_class="listing",
        allow_reorder=True,
        auto_append=False,
    )

    omail_group_encoder = schema.Bool(
        title=_(u"Activate group encoder"),
        description=_(
            u"ONCE ACTIVATED, THIS OPTION CAN'T BE EASILY UNDONE !! <br />"
            u"When activating this option, a group encoder function is added in the configuration, "
            u"a new field is added to the mail form to choose the creating group and permissions are given "
            u"to the selected creating group. Mails are then separately handled following the creating "
            u"groups. <br />The creating group can be preset in scanning program. It's then possible to have "
            u"multiple scanners and separated 'encoder' groups. "
            u"The list of 'encoder' groups, can be generated to be used in 'scanner program'."
        ),
        default=False,
    )

    # FIELDSET OEM
    model.fieldset(
        "outgoing_email",
        label=_(u"Outgoing email"),
        fields=[
            "org_email_templates_encoder_can_edit",
            "omail_close_on_email_send",
            "omail_replyto_email_send",
            "omail_sender_email_default",
            "omail_bcc_email_default",
            "omail_email_signature",
        ],
    )

    org_email_templates_encoder_can_edit = schema.Bool(
        title=_(u"Enable edition of service email templates for encoder"),
        description=_(u"Check if a service encoder can edit his service email templates."),
        default=True,
    )

    omail_close_on_email_send = schema.Bool(title=_(u"Close outgoing mail on email send"), default=True)

    omail_replyto_email_send = schema.Bool(title=_(u"Send email with sender as reply to"), default=False)

    omail_sender_email_default = schema.Choice(
        title=_(u"From where to get sender default email"),
        vocabulary=oemail_sender_email_values,
        default=u"agent_email",
    )

    omail_bcc_email_default = schema.List(
        title=_(u"Default bcc emails"),
        value_type=schema.Choice(vocabulary=oemail_bcc_email_values),
    )
    widget("omail_bcc_email_default", CheckBoxFieldWidget, multiple="multiple", size=5)

    widget("omail_email_signature", WysiwygFieldWidget)
    # widget('omail_email_signature', klass='pat-tinymce') in plone 5 ?
    omail_email_signature = schema.Text(
        title=_(u"Email signature model"),
        description=_(u"TAL compliant with variables: view, context, user, dghv, sender, request and modules."),
        required=False,
    )

    # FIELDSET CONTACTS
    model.fieldset("contact", label=_(u"Contacts"), fields=["all_backrefs_view", "contact_group_encoder"])

    all_backrefs_view = schema.Bool(title=_(u"A user can see all mail titles linked to a contact."), default=False)

    contact_group_encoder = schema.Bool(
        title=_(u"Activate group encoder"),
        description=_(
            u"ONCE ACTIVATED, THIS OPTION CAN'T BE EASILY UNDONE !! <br />"
            u"When activating this option, a group encoder function is added in the configuration, a "
            u"new field is added to the contact form to choose the creating group and permissions are given "
            u"to the selected creating group. Contacts are then separately handled following the creating "
            u"groups. <br />This option can be combined with the mail creating group option."
        ),
        default=False,
    )

    # FIELDSET OTHER
    model.fieldset(
        "general",
        label=_(u"General config tab"),
        fields=["groups_hidden_in_dashboard_filter", "users_hidden_in_dashboard_filter"],
    )

    groups_hidden_in_dashboard_filter = schema.List(
        title=_(u"Groups hidden in dashboards filter"),
        required=False,
        value_type=schema.Choice(vocabulary=u"imio.dms.mail.TreatingGroupsWithDeactivatedVocabulary"),
    )
    widget("groups_hidden_in_dashboard_filter", OrderedSelectFieldWidget, size=10)
    # widget("groups_hidden_in_dashboard_filter", MultiSelect2FieldWidget)

    users_hidden_in_dashboard_filter = schema.List(
        title=_(u"Users hidden in dashboards filter"),
        required=False,
        value_type=schema.Choice(vocabulary=u"imio.dms.mail.AssignedUsersWithDeactivatedVocabulary"),
    )
    widget("users_hidden_in_dashboard_filter", OrderedSelectFieldWidget, size=10)

    @invariant
    def validate_settings(data):  # noqa
        # called for each fieldset !
        # when changing directly in registry, data contains not the same thing: we pass validation
        if not isinstance(data.__context__, RecordsProxy):
            return
        # which fieldset ?
        fieldset = ""
        if "mail_types" in data._Data_data___:
            fieldset = "incomingmail"
        elif "iemail_routing" in data._Data_data___:
            fieldset = "incoming_email"
        elif "omail_types" in data._Data_data___:
            fieldset = "outgoingmail"
        elif "org_email_templates_encoder_can_edit" in data._Data_data___:
            fieldset = "outgoing_email"
        elif "contact_group_encoder" in data._Data_data___:
            fieldset = "contact"
        elif "groups_hidden_in_dashboard_filter" in data._Data_data___:
            fieldset = "general"
        # check ITableListSchema id uniqueness
        for fs, tab, fieldname, title in (
            ("incomingmail", "Incoming mail", "mail_types", u"Types of incoming mail"),
            ("outgoingmail", "Outgoing mail", "omail_types", u"Types of outgoing mail"),
            ("outgoingmail", "Outgoing mail", "omail_send_modes", u"Send modes"),
        ):
            if fieldset and fs != fieldset:
                continue
            ids = []
            try:
                values = getattr(data, fieldname) or []
            except NoInputData:
                continue
            for entry in values:
                if entry["value"] in ids:
                    raise Invalid(
                        _(
                            u"${tab} tab: multiple value '${value}' in '${field}' setting !! Must be unique",
                            mapping={"tab": _(tab), "value": entry["value"], "field": _(title)},
                        )
                    )
                ids.append(entry["value"])
        # check group_encoder deactivation
        for fs, tab, fld in (
            ("incomingmail", "Incoming mail", "imail_group_encoder"),
            ("outgoingmail", "Outgoing mail", "omail_group_encoder"),
            ("contact", "Contacts", "contact_group_encoder"),
        ):
            if fieldset and fs != fieldset:
                continue
            rec = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(fld)
            try:
                if api.portal.get_registry_record(rec) and not getattr(data, fld):
                    raise Invalid(
                        _(
                            u"${tab} tab: unchecking '${field}' setting is not expected !!",
                            mapping={"tab": _(tab), "field": _("Activate group encoder")},
                        )
                    )
            except NoInputData:
                pass
        # check iemail_routing
        if fieldset == "incoming_email" or not fieldset:
            for fld, fld_tit, needed in (("iemail_routing", _tr(u"${type} routing", mapping={"type": ""}),
                                          ("user_value", "tg_value")),
                                         ("iemail_state_set", _tr(u"${type} state set", mapping={"type": ""}),
                                          ("state_value", ))):
                for i, rule in enumerate(getattr(data, fld) or [], start=1):
                    # check patterns
                    for col, col_tit in (("transfer_email_pat", u"Transfer email pattern"),
                                         ("original_email_pat", u"Original email pattern")):
                        if not rule[col]:
                            continue
                        try:
                            re.compile(rule[col])
                        except re.error:
                            raise Invalid(
                                _(
                                    u"${tab} tab: « ${field} » rule ${rule} has an invalid pattern in « ${col} »",
                                    mapping={"tab": _(u"Incoming email"), "field": fld_tit, "rule": i,
                                             "col": _(col_tit)},
                                )
                            )
                    # check empty value
                    if [col for col in needed if rule.get(col) is None]:
                        raise Invalid(_(u"${tab} tab: « ${field} » rule ${rule} is configured with no values defined",
                                        mapping={"tab": _(u"Incoming email"), "field": fld_tit, "rule": i}))
                    # check user is in org
                    if fld == "iemail_routing" and not rule["tg_value"].startswith("_") and \
                            not rule["user_value"].startswith("_"):
                        pids = get_selected_org_suffix_principal_ids(rule["tg_value"], IM_EDITOR_SERVICE_FUNCTIONS)
                        if rule["user_value"] not in pids:
                            username = [t.title for t in vocabularyname_to_terms("imio.helpers.SimplySortedUsers")
                                        if t.value == rule["user_value"]][0]
                            tgname = [t.title for t in
                                      vocabularyname_to_terms("collective.dms.basecontent.treating_groups")
                                      if t.value == rule["tg_value"]][0]
                            raise Invalid(
                                _(
                                    u"${tab} tab: « ${field} » rule ${rule} is configured with an assigned user "
                                    u"« ${user} » not in the corresponding treating group « ${tg} »",
                                    mapping={"tab": _(u"Incoming email"), "field": fld_tit, "rule": i,
                                             "user": safe_unicode(username), "tg": safe_unicode(tgname)},
                                )
                            )
        # check omail_send_modes id
        if fieldset == "outgoingmail" or not fieldset:
            try:
                for dic in data.omail_send_modes or []:
                    if (
                        not dic["value"].startswith("email")
                        and not dic["value"].startswith("post")
                        and not dic["value"].startswith("other")
                    ):
                        # raise WidgetActionExecutionError("omail_send_modes",
                        #                                  Invalid(_(u"Outgoingmail tab: send_modes field must have "
                        #                                         u"values starting with 'post', 'email' or 'other'")))
                        raise Invalid(
                            _(
                                u"${tab} tab: send_modes field must have values starting with « post », « email » or "
                                u"« other »", mapping={"tab": _("Outgoing mail")},
                            )
                        )
            except NoInputData:
                pass
        # check fields
        constraints = {
            "imail_fields": {
                "fieldset": "incomingmail",
                "voc": IMFieldsVocabulary()(None),
                "mand": [
                    "IDublinCore.title",
                    "IDublinCore.description",
                    "orig_sender_email",
                    "sender",
                    "treating_groups",
                    "ITask.assigned_user",
                    "recipient_groups",
                    "reception_date",
                    "mail_type",
                    "reply_to",
                    "internal_reference_no",
                ],
                "not": [
                    "ITask.due_date",
                    "ITask.task_description",
                    "external_reference_no",
                    "original_mail_date",
                    "IClassificationFolder.classification_categories",
                    "IClassificationFolder.classification_folders",
                    "document_in_service",
                    "IDmsMailCreatingGroup.creating_group",
                ],
                "pos": ["IDublinCore.title", "IDublinCore.description"],
            },
            "omail_fields": {
                "fieldset": "outgoingmail",
                "voc": OMFieldsVocabulary()(None),
                "mand": [
                    "IDublinCore.title",
                    "IDublinCore.description",
                    "orig_sender_email",
                    "recipients",
                    "treating_groups",
                    "ITask.assigned_user",
                    "sender",
                    "recipient_groups",
                    "send_modes",
                    "reply_to",
                    "outgoing_date",
                    "internal_reference_no",
                    "email_status",
                    "email_subject",
                    "email_sender",
                    "email_recipient",
                    "email_cc",
                    "email_bcc",
                    "email_attachments",
                    "email_body",
                ],
                "not": [
                    "mail_type",
                    "mail_date",
                    "ITask.due_date",
                    "ITask.task_description",
                    "external_reference_no",
                    "IClassificationFolder.classification_categories",
                    "IClassificationFolder.classification_folders",
                    "document_in_service",
                    "IDmsMailCreatingGroup.creating_group",
                ],
                "pos": ["IDublinCore.title", "IDublinCore.description"],
            },
        }
        missing = {}
        position = {}
        for conf in constraints:
            if fieldset and fieldset != constraints[conf]["fieldset"]:
                continue
            old_value = api.portal.get_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(conf), default=[]
            )
            try:
                value = getattr(data, conf) or []
            except NoInputData:
                continue
            if value == old_value:  # the validator passes multiple times here but not always with the new value
                continue
            flds = [field["field_name"] for field in value]
            for mand in constraints[conf]["mand"]:
                if mand not in flds:
                    missing_cf = missing.setdefault(conf, [])
                    missing_cf.append(mand)
            for i, field in enumerate(constraints[conf]["pos"]):
                if field is None:
                    continue
                if flds[i] != field:
                    pos_cf = position.setdefault(conf, [])
                    pos_cf.append((field, i))
        msg = u""
        for conf in missing:
            fields = [u"'{}'".format(constraints[conf]["voc"].getTerm(mfld).title) for mfld in missing[conf]]
            msg += _tr(u"for '${conf}' config => ${fields}. ", mapping={"conf": _tr(conf), "fields": ", ".join(fields)})
        if msg:
            raise Invalid(_tr(u"Missing mandatory fields: ${msg}", mapping={"msg": msg}))
        msg = u""
        for conf in position:
            fields = [
                _tr(
                    u"'${field}': position ${position}",
                    mapping={"field": constraints[conf]["voc"].getTerm(mfld).title, "position": pos + 1},
                )
                for mfld, pos in position[conf]
            ]
            msg += _tr(u"for '${conf}' config => ${fields}. ", mapping={"conf": _tr(conf), "fields": ", ".join(fields)})
        if msg:
            raise Invalid(_tr(u"Position required for fields: ${msg}", mapping={"msg": msg}))


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
        filt_groups = {"incomingmail": "imail_fields", "outgoingmail": "omail_fields"}
        for grp in self.groups:
            if grp.__name__ not in filt_groups:
                continue
            wdg = grp.widgets[filt_groups[grp.__name__]]
            def_values = [row["field_name"] for row in wdg.value]
            voc_name = wdg.field.value_type.schema["field_name"].vocabularyName
            voc = getUtility(IVocabularyFactory, voc_name)(self.context)
            unconfigured = [u'"{}"'.format(t.title) for t in voc._terms if t.value not in def_values]
            if unconfigured:
                wdg.field = copy.copy(wdg.field)
                wdg.field.description = u"{}<br />{}".format(
                    _tr(u"Configure this carefully. You can order with arrows."),
                    _tr(
                        u"<span class='unconfigured-fields'>Unconfigured fields are: ${list}</span>",
                        mapping={"list": u", ".join(unconfigured)},
                    ),
                )


SettingsView = layout.wrap_form(SettingsEditForm, ControlPanelFormWrapper)


def imiodmsmail_settings_changed(event):
    """Manage a record change"""
    if (
        IRecordModifiedEvent.providedBy(event)
        and event.record.interfaceName
        and event.record.interface not in (IImioDmsMailConfig, IImioDmsMailConfig2)
    ):
        return
    if event.record.fieldName == "mail_types":
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.IMMailTypesVocabulary")
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.IMActiveMailTypesVocabulary")
    if event.record.fieldName == "omail_types":
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.OMMailTypesVocabulary")
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.OMActiveMailTypesVocabulary")
    if event.record.fieldName == "omail_send_modes":
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.OMActiveSendModesVocabulary")
    if event.record.fieldName == "assigned_user_check":
        update_transitions_auc_config("dmsincomingmail")  # i_e ok
        n_plus_x = "imio.dms.mail.wfadaptations.IMServiceValidation" in [
            adapt["adaptation"] for adapt in get_applied_adaptations()
        ]
        snoi = False
        if event.newValue == u"no_check" or not n_plus_x:
            snoi = True
        portal = api.portal.get()
        folder = portal["incoming-mail"]["mail-searches"]
        if folder["to_treat_in_my_group"].showNumberOfItems != snoi:
            folder["to_treat_in_my_group"].showNumberOfItems = snoi  # noqa
            folder["to_treat_in_my_group"].reindexObject()
    if event.record.fieldName in ("org_templates_encoder_can_edit", "org_email_templates_encoder_can_edit"):
        folder_id = ("email" in event.record.fieldName) and "oem" or "om"
        portal = api.portal.get()
        main_folder = portal.templates[folder_id]
        s_orgs = get_registry_organizations()
        roles = ["Reader"]
        all_roles = ["Reader", "Contributor", "Editor"]
        if api.portal.get_registry_record(event.record.__name__):
            roles = list(all_roles)
        for uid in s_orgs:
            if uid not in main_folder:
                continue
            folder = main_folder[uid]
            groupname = "{}_encodeur".format(uid)
            api.group.revoke_roles(groupname=groupname, roles=all_roles, obj=folder)
            api.group.grant_roles(groupname=groupname, roles=roles, obj=folder)

    if event.record.fieldName == "imail_group_encoder":
        if api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.imail_group_encoder"):
            configure_group_encoder("imail_group_encoder")
    if event.record.fieldName == "omail_group_encoder":
        if api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_group_encoder"):
            # configure_group_encoder(['dmsoutgoingmail', 'dmsoutgoing_email'])
            configure_group_encoder("omail_group_encoder")
    if event.record.fieldName == "contact_group_encoder":
        if api.portal.get_registry_record("imio.dms.mail.browser.settings.IImioDmsMailConfig.contact_group_encoder"):
            configure_group_encoder("contact_group_encoder", contacts_part=True)
            # set permission on contacts directory
            portal = api.portal.get()
            portal["contacts"].manage_permission(
                "imio.dms.mail: Write mail base fields", ("Manager", "Site Administrator", "Contributor"), acquire=1
            )
    if event.record.fieldName == "groups_hidden_in_dashboard_filter":
        invalidate_cachekey_volatile_for("imio.dms.mail.vocabularies.TreatingGroupsForFacetedFilterVocabulary")
    if event.record.fieldName == "imail_folder_period" and event.newValue is not None:
        portal = api.portal.get()
        setattr(portal[MAIN_FOLDERS["dmsincomingmail"]], "folder_period", event.newValue)
    if event.record.fieldName == "omail_folder_period" and event.newValue is not None:
        portal = api.portal.get()
        setattr(portal[MAIN_FOLDERS["dmsoutgoingmail"]], "folder_period", event.newValue)


def set_group_encoder_on_existing_types(portal_types, portal=None, index=None):
    if portal is None:
        portal = api.portal.get()
    for brain in portal.portal_catalog.unrestrictedSearchResults(portal_type=portal_types):
        obj = brain._unrestrictedGetObject()
        if ensure_set_field(obj, "creating_group", default_creating_group(obj.getOwner())) and index is not None:
            obj.reindexObject([index])


def configure_group_encoder(field_name, contacts_part=False):
    """
    Used to configure a creating function and group for some internal organizations.
    Update portal_type to add behavior, configure localroles field
    """
    portal_types = GE_CONFIG[field_name]["pt"]
    # function
    functions = get_registry_functions()
    if CREATING_GROUP_SUFFIX not in [fct["fct_id"] for fct in functions]:
        functions.append(
            {
                "fct_title": u"Indicateur du service",
                "fct_id": CREATING_GROUP_SUFFIX,
                "fct_orgs": [],
                "fct_management": False,
                "enabled": True,
            }
        )
        set_registry_functions(functions)
    if contacts_part and CONTACTS_PART_SUFFIX not in [fct["fct_id"] for fct in functions]:
        functions.append(
            {
                "fct_title": u"Contacts par défaut",
                "fct_id": CONTACTS_PART_SUFFIX,
                "fct_orgs": [],
                "fct_management": False,
                "enabled": True,
            }
        )
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
        "dmsincomingmail": {  # i_e ok
            "created": {
                CREATING_GROUP_SUFFIX: {
                    "roles": [
                        "Contributor",
                        "Editor",
                        "DmsFile Contributor",
                        "Base Field Writer",
                        "Treating Group Writer",
                    ]
                }
            },
            #                                                          CREATING_FIELD_ROLE]}},
            "proposed_to_manager": {CREATING_GROUP_SUFFIX: {"roles": ["Base Field Writer", "Reader"]}},
            "proposed_to_agent": {CREATING_GROUP_SUFFIX: {"roles": ["Reader"]}},
            "in_treatment": {CREATING_GROUP_SUFFIX: {"roles": ["Reader"]}},
            "closed": {CREATING_GROUP_SUFFIX: {"roles": ["Reader"]}},
        },
        "dmsincoming_email": {
            "created": {
                CREATING_GROUP_SUFFIX: {
                    "roles": [
                        "Contributor",
                        "Editor",
                        "DmsFile Contributor",
                        "Base Field Writer",
                        "Treating Group Writer",
                    ]
                }
            },
            #                                                          CREATING_FIELD_ROLE]}},
            "proposed_to_manager": {CREATING_GROUP_SUFFIX: {"roles": ["Base Field Writer", "Reader"]}},
            "proposed_to_agent": {CREATING_GROUP_SUFFIX: {"roles": ["Reader"]}},
            "in_treatment": {CREATING_GROUP_SUFFIX: {"roles": ["Reader"]}},
            "closed": {CREATING_GROUP_SUFFIX: {"roles": ["Reader"]}},
        },
        "dmsoutgoingmail": {
            "to_be_signed": {CREATING_GROUP_SUFFIX: {"roles": ["Editor", "Reviewer"]}},
            "sent": {CREATING_GROUP_SUFFIX: {"roles": ["Reader", "Reviewer"]}},
            "scanned": {
                CREATING_GROUP_SUFFIX: {
                    "roles": [
                        "Contributor",
                        "Editor",
                        "Reviewer",
                        "DmsFile Contributor",
                        "Base Field Writer",
                        "Treating Group Writer",
                    ]
                }
            },
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
    if "dmsincomingmail" in portal_types:  # i_e ok
        for typ in ("dmsincomingmail", "dmsincoming_email"):
            states = list_wf_states(portal, typ)
            for st_id, st_tit in states:
                if st_id.startswith("proposed_to_n_plus_"):
                    config[typ][st_id] = {CREATING_GROUP_SUFFIX: {"roles": ["Reader"]}}

    # criterias config
    criterias = {
        "dmsincomingmail": ("incoming-mail", "mail-searches", "all_mails"),  # i_e ok
        "dmsoutgoingmail": ("outgoing-mail", "mail-searches", "all_mails"),
        "organization": ("contacts", "orgs-searches", "all_orgs"),
        "person": ("contacts", "persons-searches", "all_persons"),
        "held_position": ("contacts", "hps-searches", "all_hps"),
        "contact_list": ("contacts", "cls-searches", "all_cls"),
    }

    for portal_type in portal_types:
        # behaviors
        fti = getUtility(IDexterityFTI, name=portal_type)
        # try:
        #     fti = getUtility(IDexterityFTI, name=portal_type)
        # except ComponentLookupError:
        #     continue
        if "imio.dms.mail.content.behaviors.IDmsMailCreatingGroup" not in fti.behaviors:
            old_bav = tuple(fti.behaviors)
            fti.behaviors = tuple(list(fti.behaviors) + ["imio.dms.mail.content.behaviors.IDmsMailCreatingGroup"])
            ftiModified(fti, ObjectModifiedEvent(fti, DexterityFTIModificationDescription("behaviors", old_bav)))

        # local roles
        if config.get(portal_type):
            msg = add_fti_configuration(portal_type, config[portal_type], keyname="creating_group")
            if msg:
                logger.warn(msg)

        # criterias
        folder_id, category_id, default_id = criterias.get(portal_type, ("", "", ""))
        if folder_id:
            reimport_faceted_config(
                portal[folder_id][category_id],
                xml="mail-searches-group-encoder.xml",
                default_UID=portal[folder_id][category_id][default_id].UID(),
            )

    # display added field for im and om
    if not contacts_part:
        config = {"dmsincomingmail": "imail", "dmsoutgoingmail": "omail"}
        key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}_fields".format(config[portal_types[0]])
        fields = api.portal.get_registry_record(key)
        if "IDmsMailCreatingGroup.creating_group" not in [f["field_name"] for f in fields]:
            fields.append(
                {
                    "field_name": "IDmsMailCreatingGroup.creating_group",
                    "read_tal_condition": u"",
                    "write_tal_condition": u"",
                }
            )
            api.portal.set_registry_record(key, fields)

    # set a value on existing content
    set_group_encoder_on_existing_types(portal_types, portal=portal, index=GE_CONFIG[field_name]["idx"])


class IImioDmsMailConfig2(Interface):
    """Schema used as registry record prefixed as 'imio.dms.mail'.

    It avoids that values are overwrited by registry step!"""

    dv_clean_days = schema.Int(
        title=_(u"Document viewer preservation days number"),
    )

    dv_clean_date = schema.Date(
        title=_(u"Document viewer preservation date"),
    )

    imail_folder_period = schema.TextLine(
        title=_(u"Incoming mails folder period (month, week, day)"),
    )

    omail_folder_period = schema.TextLine(
        title=_(u"Outgoing mails folder period (month, week, day)"),
    )

    product_version = schema.TextLine(
        title=_(u"Current product version"),
    )
