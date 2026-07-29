# -*- coding: utf-8 -*-
"""Vocabularies."""
from collective.contact.plonegroup.behaviors import PrimaryOrganizationsVocabulary
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.interfaces import INotPloneGroupContact
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_person_from_userid
from collective.contact.plonegroup.utils import get_selected_org_suffix_principal_ids
from collective.contact.plonegroup.utils import organizations_with_suffixes
from collective.iconifiedcategory.utils import calculate_category_id
from collective.iconifiedcategory.vocabularies import CategoryVocabulary
from ftw.labels.interfaces import ILabelJar
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.dms.mail import ALL_SERVICE_FUNCTIONS
from imio.dms.mail import CONTACTS_PART_SUFFIX
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import FIRST_LEVEL_TABS
from imio.dms.mail import OM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.utils import get_context_with_request
from imio.dms.mail.utils import list_wf_states
from imio.helpers import EMPTY_STRING
from imio.helpers import EMPTY_TITLE
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.vocabularies import voc_cache_key as users_groups_cache_key
from natsort import humansorted
from operator import attrgetter
from plone import api
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize import ram
from Products.CMFPlone import PloneMessageFactory as pmf
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from unidecode import unidecode  # unidecode_expect_nonascii not yet available in used version
from z3c.formwidget.query.interfaces import IQuerySource
from zope.component import getUtility
from zope.component import queryUtility
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import re


def voc_cache_key(method, self, context):
    """Returns a persistent portal stored date following the given cache key.

    Must be programatically invalidated."""
    return get_cachekey_volatile("%s.%s" % (self.__class__.__module__, self.__class__.__name__))


@implementer(IVocabularyFactory)
class BaseReviewStatesVocabulary(object):
    """Base wf states vocabulary: lists self.portal_type states, in configured order"""

    portal_type = None
    site_language = True  # translate in site language, otherwise negotiate with request

    def __call__(self, context):
        if self.site_language:
            tl = api.portal.get().portal_properties.site_properties.getProperty("default_language", "fr")
            kwargs = {"target_language": tl}
        else:
            kwargs = {"context": context.REQUEST}
        return SimpleVocabulary(
            [
                SimpleVocabulary.createTerm(st_id, st_id, translate(safe_unicode(st_tit), domain="plone", **kwargs))
                for st_id, st_tit in list_wf_states(context, self.portal_type)
            ]
        )


class IMReviewStatesVocabulary(BaseReviewStatesVocabulary):
    """Incoming mail states vocabulary"""

    portal_type = "dmsincomingmail"  # i_e ok


class OMReviewStatesVocabulary(BaseReviewStatesVocabulary):
    """Outgoing mail states vocabulary"""

    portal_type = "dmsoutgoingmail"


class SRReviewStatesVocabulary(BaseReviewStatesVocabulary):
    """Sign request states vocabulary"""

    portal_type = "sign_request"


class TaskReviewStatesVocabulary(BaseReviewStatesVocabulary):
    """Task states vocabulary"""

    portal_type = "task"
    site_language = False


@implementer(IVocabularyFactory)
class FirstLevelTabsVocabulary(object):
    """First level tabs vocabulary (used to configure displayed tabs)"""

    def __call__(self, context):
        portal = api.portal.get()
        terms = []
        for tab_id in FIRST_LEVEL_TABS:
            folder = portal.get(tab_id)
            title = folder is not None and safe_unicode(folder.Title()) or safe_unicode(tab_id)
            terms.append(SimpleVocabulary.createTerm(tab_id, tab_id, title))
        return SimpleVocabulary(terms)


class ContactsReviewStatesVocabulary(BaseReviewStatesVocabulary):
    """Contacts states vocabulary"""

    portal_type = "organization"
    site_language = False


@implementer(IVocabularyFactory)
class HeldPositionUsagesVocabulary(object):
    """Vocabulary for held position usages."""

    def __call__(self, context):
        res = [
            # SimpleTerm(EMPTY_STRING, EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers")),
            SimpleTerm("signer", "signer", _("Signer")),
            SimpleTerm("approving", "approving", _("Approving"))
        ]
        return SimpleVocabulary(res)


@implementer(IVocabularyFactory)
class AssignedUsersWithDeactivatedVocabulary(object):
    """All users, activated first."""

    @ram.cache(users_groups_cache_key)
    def AssignedUsersWithDeactivatedVocabulary__call__(self, context):
        factory = getUtility(IVocabularyFactory, "plone.principalsource.Users")
        vocab = factory(context)  # terms as username, userid, fullname
        a_terms = []
        d_terms = []
        active_orgs = get_registry_organizations()
        functions = [dic["fct_id"] for dic in get_registry_functions()]
        for term in vocab:
            # with ldap (tournai), some term have value, token and title not ascii !!
            # term.value = safe_unicode(term.value)
            term.token = safe_unicode(term.token)
            for groupid in get_plone_groups_for_user(user_id=term.token):  # token is the userid
                if groupid == "AuthenticatedUsers":
                    continue
                parts = groupid.split("_")
                if len(parts) != 1:
                    group_suffix = "_".join(parts[1:])
                    if group_suffix in functions and parts[0] not in active_orgs:  # not an active org
                        continue
                term.title = safe_unicode(term.title)
                a_terms.append(term)
                break
            else:
                term.title = _tr("${element_title} (Inactive)", mapping={"element_title": safe_unicode(term.title)})
                d_terms.append(term)
        return SimpleVocabulary(
            [SimpleTerm(EMPTY_STRING, EMPTY_STRING, _tr(EMPTY_TITLE, "imio.helpers"))]
            + humansorted(a_terms, key=attrgetter("title"))
            + humansorted(d_terms, key=attrgetter("title"))
        )

    __call__ = AssignedUsersWithDeactivatedVocabulary__call__


@implementer(IVocabularyFactory)
class AssignedUsersForFacetedFilterVocabulary(object):
    """All users, activated first."""

    def __call__(self, context):
        factory = getUtility(IVocabularyFactory, "imio.dms.mail.AssignedUsersWithDeactivatedVocabulary")
        vocab = factory(context)
        hidden_users = api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.users_hidden_in_dashboard_filter", default=[]
        )
        return SimpleVocabulary([term for term in vocab._terms if term.value not in hidden_users])


def get_settings_vta_table(field, active=(True, False), choose=False):
    """
    Create a vocabulary from registry table variable (value, title, active)
    """
    key = "imio.dms.mail.browser.settings.IImioDmsMailConfig.{}".format(field)
    terms = []
    id_utility = queryUtility(IIDNormalizer)
    for mail_type in api.portal.get_registry_record(key, default=[]) or []:
        # value (stored), token (request), title
        if mail_type["active"] in active:
            val = mail_type["value"]
            if val == "none":
                val = None
                choose = False
            terms.append(SimpleTerm(val, id_utility.normalize(mail_type["value"]), mail_type["dtitle"]))
    if choose:
        terms.insert(0, SimpleTerm(None, "", _("Choose a value !")))
    return SimpleVocabulary(terms)


@implementer(IVocabularyFactory)
class IMMailTypesVocabulary(object):
    """Mail types vocabulary"""

    @ram.cache(voc_cache_key)
    def IMMailTypesVocabulary__call__(self, context):
        return get_settings_vta_table("mail_types")

    __call__ = IMMailTypesVocabulary__call__


@implementer(IVocabularyFactory)
class IMActiveMailTypesVocabulary(object):
    """Active mail types vocabulary"""

    @ram.cache(voc_cache_key)
    def IMActiveMailTypesVocabulary__call__(self, context):
        return get_settings_vta_table("mail_types", choose=True, active=[True])

    __call__ = IMActiveMailTypesVocabulary__call__


@implementer(IVocabularyFactory)
class PloneGroupInterfacesVocabulary(object):
    """List interfaces that will be shown in contacts faceted navigation."""

    def __call__(self, context):
        interfaces = [IPloneGroupContact, INotPloneGroupContact, IPersonnelContact]

        terms = [
            SimpleVocabulary.createTerm(interface.__identifier__, interface.__identifier__, interface.__name__)
            for interface in interfaces
        ]

        return SimpleVocabulary(terms)


def get_internal_held_positions_vocabulary(states=(), usages=(), as_person=False):
    """Returns a vocabulary with internal held positions, following given states list.
    The vocabulary is sorted following firstname sort option.
    """
    catalog = api.portal.get_tool("portal_catalog")
    sfs = api.portal.get_registry_record(
        "imio.dms.mail.browser.settings.IImioDmsMailConfig.omail_sender_firstname_sorting"
    )
    sort_on = ["firstname", "lastname"]
    sfs or sort_on.reverse()

    criterias = {
        "portal_type": "held_position",
        "object_provides": "imio.dms.mail.interfaces.IPersonnelContact",
    }
    if states:
        criterias["review_state"] = states
    if usages:
        criterias["usages"] = usages
    brains = catalog.unrestrictedSearchResults(**criterias)

    terms = []
    terms_dict = {}
    for brain in brains:
        hp = brain._unrestrictedGetObject()
        person = hp.get_person()
        org = hp.get_organization()
        if org is None:
            continue
        if as_person:
            if not person.userid:
                continue
            if person.userid not in terms_dict:
                terms_dict[person.userid] = (
                    person,
                    SimpleTerm(person.UID(), person.userid, person.get_title(include_person_title=False))
                )
        else:
            terms.append(
                (
                    person,
                    hp,
                    SimpleTerm(
                        brain.UID,
                        "{}_{}_{}".format(brain.UID, org.UID(), person.userid or ""),
                        hp.get_full_title(first_index=1),
                    ),
                )
            )

    def sort_persons(t):
        return getattr(t[0], sort_on[0]), getattr(t[0], sort_on[1])

    def sort_hps(t):
        return getattr(t[0], sort_on[0]), getattr(t[0], sort_on[1]), t[1].get_full_title(first_index=1)

    if as_person:
        return SimpleVocabulary([term for pers, term in sorted(terms_dict.values(), key=sort_persons)])
    else:
        return SimpleVocabulary([term for pers, hpo, term in sorted(terms, key=sort_hps)])


@implementer(IVocabularyFactory)
class OMActiveSenderVocabulary(object):
    """
    Outgoing mail sender vocabulary
    term value = hp uid
    term token = org uid _ userid
    term title = hp title
    """

    @ram.cache(voc_cache_key)
    def OMActiveSenderVocabulary__call__(self, context):
        return get_internal_held_positions_vocabulary(["active"])

    __call__ = OMActiveSenderVocabulary__call__


@implementer(IVocabularyFactory)
class OMSenderVocabulary(object):
    """
    Outgoing mail sender vocabulary
    term value = hp uid
    term token = org uid _ userid
    term title = hp title
    """

    @ram.cache(voc_cache_key)
    def OMSenderVocabulary__call__(self, context):
        return get_internal_held_positions_vocabulary(["active", "deactivated"])

    __call__ = OMSenderVocabulary__call__


@implementer(IVocabularyFactory)
class OMMailTypesVocabulary(object):
    """Mail types vocabulary"""

    @ram.cache(voc_cache_key)
    def OMMailTypesVocabulary__call__(self, context):
        return get_settings_vta_table("omail_types")

    __call__ = OMMailTypesVocabulary__call__


@implementer(IVocabularyFactory)
class OMActiveMailTypesVocabulary(object):
    """Active mail types vocabulary"""

    @ram.cache(voc_cache_key)
    def OMActiveMailTypesVocabulary__call__(self, context):
        return get_settings_vta_table("omail_types", active=[True])

    __call__ = OMActiveMailTypesVocabulary__call__


@implementer(IVocabularyFactory)
class OMSendModesVocabulary(object):
    """All send modes vocabulary"""

    @ram.cache(voc_cache_key)
    def OMSendModesVocabulary__call__(self, context):
        return get_settings_vta_table("omail_send_modes")

    __call__ = OMSendModesVocabulary__call__


@implementer(IVocabularyFactory)
class OMActiveSendModesVocabulary(object):
    """Active send modes vocabulary"""

    @ram.cache(voc_cache_key)
    def OMActiveSendModesVocabulary__call__(self, context):
        return get_settings_vta_table("omail_send_modes", active=[True])

    __call__ = OMActiveSendModesVocabulary__call__


@implementer(IVocabularyFactory)
class IMSendModesVocabulary(object):
    """All incoming send modes vocabulary"""

    @ram.cache(voc_cache_key)
    def IMSendModesVocabulary__call__(self, context):
        return get_settings_vta_table("imail_send_modes")

    __call__ = IMSendModesVocabulary__call__


@implementer(IVocabularyFactory)
class IMActiveSendModesVocabulary(object):
    """Active incoming send modes vocabulary"""

    @ram.cache(voc_cache_key)
    def IMActiveSendModesVocabulary__call__(self, context):
        return get_settings_vta_table("imail_send_modes", active=[True])

    __call__ = IMActiveSendModesVocabulary__call__


@implementer(IVocabularyFactory)
class OMSignersVocabulary(object):
    """Signers vocabulary"""

    @ram.cache(voc_cache_key)
    def OMSignersVocabulary__call__(self, context):
        return get_internal_held_positions_vocabulary(usages="signer")

    __call__ = OMSignersVocabulary__call__


@implementer(IVocabularyFactory)
class SigningApprovingsVocabulary(object):

    @ram.cache(voc_cache_key)
    def SigningApprovingsVocabulary__call__(self, context):
        return SimpleVocabulary(
            [
                SimpleTerm(value=u"_empty_", title=_("* No validation")),
                SimpleTerm(value=u"_themself_", title=_("* Themself")),
            ] + get_internal_held_positions_vocabulary(usages="approving", as_person=True)._terms
        )

    __call__ = SigningApprovingsVocabulary__call__


@implementer(IVocabularyFactory)
class SigningRequestApprovingsVocabulary(object):
    """Same as SigningApprovingsVocabulary but without the "_empty_" value."""

    @ram.cache(voc_cache_key)
    def SigningRequestApprovingsVocabulary__call__(self, context):
        return SimpleVocabulary(
            [
                SimpleTerm(value=u"_themself_", title=_("* Themself")),
            ] + get_internal_held_positions_vocabulary(usages="approving", as_person=True)._terms
        )

    __call__ = SigningRequestApprovingsVocabulary__call__


def encodeur_active_orgs(context):
    """This vocabulary source is used on the OM treating_groups field.

    :param context:
    :return: a filtered vocabulary with the user treating groups (primary organization user is the first)
    """
    current_user = api.user.get_current()
    factory = getUtility(IVocabularyFactory, u"collective.dms.basecontent.treating_groups")
    voc = factory(context)
    # this is the case when calling ++widget++...
    if current_user.getId() is None:
        return voc
    # the expedition group must have all values
    groups = get_plone_groups_for_user(user=current_user)
    if "expedition" in groups:
        return voc
    # we filter orgs if
    #   * current user is not admin
    #   * portal_type is not dmsoutgoingmail (on adding or reply)
    #   * state is created
    if not current_user.has_role(["Manager", "Site Administrator"]) and (
        context.portal_type != "dmsoutgoingmail" or api.content.get_state(context) == "created"
    ):
        orgs = organizations_with_suffixes(
            get_plone_groups_for_user(user=current_user), OM_EDITOR_SERVICE_FUNCTIONS, group_as_str=True
        )
        pers = get_person_from_userid(current_user.getId())
        if pers and pers.primary_organization and pers.primary_organization in orgs:
            return SimpleVocabulary(
                [voc.vocab.getTerm(pers.primary_organization)]
                + [term for term in voc.vocab._terms if term.value in orgs and term.value != pers.primary_organization]
            )
        else:
            return SimpleVocabulary([term for term in voc.vocab._terms if term.value in orgs])
    return voc


alsoProvides(encodeur_active_orgs, IContextSourceBinder)


@implementer(IVocabularyFactory)
class SignRequestActiveOrgsVocabulary(object):
    """This vocabulary only keeps organizations that have at least one user defined in their
    '<org_uid>_demand_sign' Plone group.

    The result is cached on the '_users_groups_value' volatile, which is invalidated
    on group (un)assignment and on plonegroup registry changes (see subscribers).
    """

    @ram.cache(users_groups_cache_key)
    def SignRequestActiveOrgsVocabulary__call__(self, context):
        factory = getUtility(IVocabularyFactory, u"collective.dms.basecontent.treating_groups")
        voc = factory(context)
        terms = [
            term for term in voc.vocab._terms if get_selected_org_suffix_principal_ids(term.value, [u"demand_sign"])
        ]
        return SimpleVocabulary(terms)

    __call__ = SignRequestActiveOrgsVocabulary__call__


def signrequest_active_orgs(context):
    """This vocabulary source is used on the sign_request treating_groups field.

    It is based on the named 'imio.dms.mail.SignRequestActiveOrgsVocabulary' and puts the current user
    primary organization first when it is part of the list or the user is only in one demand_sign group (org).

    :param context:
    :return: the (possibly reordered) organizations vocabulary
    """
    factory = getUtility(IVocabularyFactory, u"imio.dms.mail.SignRequestActiveOrgsVocabulary")
    voc = factory(context)
    current_user = api.user.get_current()
    # this is the case when calling ++widget++...
    if current_user.getId() is None:
        return voc
    # we filter orgs if
    #   * current user is not admin
    #   * portal_type is not sign_request (on adding)
    #   * state is created
    if not current_user.has_role(["Manager", "Site Administrator"]) and (
        context.portal_type != "sign_request" or api.content.get_state(context) == "created"
    ):
        pers = get_person_from_userid(current_user.getId())
        first_org = None
        if pers and pers.primary_organization and pers.primary_organization in voc.by_value:
            first_org = pers.primary_organization
        else:
            groups = get_plone_groups_for_user(user=current_user)
            orgs = [
                org
                for org in organizations_with_suffixes(groups, [u"demand_sign"], group_as_str=True)
                if org in voc.by_value
            ]
            if len(orgs) == 1:
                first_org = orgs[0]
        if first_org:
            return SimpleVocabulary(
                [voc.getTerm(first_org)] + [term for term in voc._terms if term.value != first_org]
            )
    return voc


alsoProvides(signrequest_active_orgs, IContextSourceBinder)


@implementer(IVocabularyFactory)
class MyLabelsVocabulary(object):
    """My Labels vocabulary. Creating a vocabulary for connected user labels"""

    def __call__(self, context):
        terms = []
        try:
            adapted = ILabelJar(context)
        except:  # noqa
            return SimpleVocabulary(terms)
        user = api.user.get_current()
        for label in adapted.list():
            if label["by_user"]:
                terms.append(
                    SimpleVocabulary.createTerm(
                        "%s:%s" % (user.getId(), label["label_id"]),
                        "%s_%s" % (user.getId(), label["label_id"]),
                        safe_unicode(label["title"]),
                    )
                )
        return SimpleVocabulary(terms)


@implementer(IVocabularyFactory)
class LabelsVocabulary(object):
    """Global labels vocabulary"""

    def LabelsVocabulary__call__(self, context):
        terms = []
        context = get_context_with_request(context)
        try:
            adapted = ILabelJar(context)
        except:  # noqa
            return SimpleVocabulary(terms)
        for label in adapted.list():
            if not label["by_user"]:
                terms.append(
                    SimpleVocabulary.createTerm(label["label_id"], label["label_id"], safe_unicode(label["title"]))
                )
        return SimpleVocabulary(terms)

    __call__ = LabelsVocabulary__call__


@implementer(IVocabularyFactory)
class CreatingGroupVocabulary(object):
    """Creating group vocabulary"""

    @ram.cache(voc_cache_key)
    def CreatingGroupVocabulary__call__(self, context):
        terms = []
        factory = getUtility(IVocabularyFactory, "collective.contact.plonegroup.organization_services")
        vocab = factory(context)

        # we get all orgs where there are plone groups with the creating group suffix
        gpm = context.acl_users.source_groups._group_principal_map
        to_keep = organizations_with_suffixes(
            gpm.keys(), [CREATING_GROUP_SUFFIX, CONTACTS_PART_SUFFIX], group_as_str=True
        )
        for term in vocab:
            if term.value in to_keep:
                terms.append(term)
        return SimpleVocabulary(terms)

    __call__ = CreatingGroupVocabulary__call__


@implementer(IVocabularyFactory)
class ActiveCreatingGroupVocabulary(object):
    """Active creating group vocabulary"""

    @ram.cache(voc_cache_key)
    def ActiveCreatingGroupVocabulary__call__(self, context):
        terms = []
        factory = getUtility(IVocabularyFactory, "collective.contact.plonegroup.organization_services")
        vocab = factory(context)

        # we get all orgs where there are plone groups with the creating group suffix and with users
        to_keep = set(
            get_organizations(
                not_empty_suffix=CREATING_GROUP_SUFFIX, only_selected=False, the_objects=False, caching=False
            )
        )
        to_keep |= set(
            get_organizations(
                not_empty_suffix=CONTACTS_PART_SUFFIX, only_selected=False, the_objects=False, caching=False
            )
        )
        for term in vocab:
            if term.value in to_keep:
                terms.append(term)
        return SimpleVocabulary(terms)

    __call__ = ActiveCreatingGroupVocabulary__call__


@implementer(IQuerySource)
class SourceAbleVocabulary(object):

    vocabulary_name = ""
    vocabulary = None

    def __init__(self, context):
        self.context = context
        if self.vocabulary_name:
            voc_inst = getUtility(IVocabularyFactory, self.vocabulary_name)
            self.vocabulary = voc_inst(self.context)
        self.__contains__ = self.vocabulary.__contains__
        self.getTerm = self.vocabulary.getTerm
        self.getTermByToken = self.vocabulary.getTermByToken
        if base_hasattr(self.vocabulary, "flattened_titles"):
            self.flattened_titles = self.vocabulary.flattened_titles
        else:
            self.decoded_titles()

    def __iter__(self):
        for term in self.vocabulary._terms:
            yield term

    def decoded_titles(self):
        self.flattened_titles = {}
        for term in self.vocabulary._terms:
            self.flattened_titles[term.value] = "".join(
                ["|%s" % p for p in re.findall(r"\w+", unidecode(safe_unicode(term.title)).lower()) if len(p) > 1]
            )

    def search(self, query_string):
        searched = ["|%s" % unidecode(safe_unicode(p)).lower() for p in query_string.split(" ")]
        return [t for t in self.vocabulary._terms if all([s in self.flattened_titles[t.value] for s in searched])]


@implementer(IContextSourceBinder)
class SourceAbleContextBinder(object):
    source_class = None

    def __call__(self, context):
        return self.source_class(context)


class ServicesSourceAbleVocabulary(SourceAbleVocabulary):
    vocabulary_name = u"collective.dms.basecontent.recipient_groups"


class ServicesSourceBinder(SourceAbleContextBinder):
    source_class = ServicesSourceAbleVocabulary


@implementer(IVocabularyFactory)
class ActionCategoriesVocabularyFactory(object):
    """Provides an actions categories vocabulary"""

    def __call__(self, context):
        portal_actions = api.portal.get_tool("portal_actions")

        categories = portal_actions.objectIds()
        categories.sort()
        return SimpleVocabulary([SimpleTerm(cat, title=cat) for cat in categories])


@implementer(IVocabularyFactory)
class IMPortalTypesVocabulary(object):
    """"""

    def __call__(self, context):
        return SimpleVocabulary(
            [
                SimpleTerm("dmsincomingmail", title=pmf(u"Incoming Mail")),
                SimpleTerm("dmsincoming_email", title=pmf(u"Incoming Email")),
            ]
        )


@implementer(IVocabularyFactory)
class TreatingGroupsWithDeactivatedVocabulary(object):
    """Get all groups, activated first."""

    @ram.cache(voc_cache_key)
    def TreatingGroupsWithDeactivatedVocabulary__call__(self, context):
        active_orgs = get_organizations(only_selected=True)
        not_active_orgs = [org for org in get_organizations(only_selected=False) if org not in active_orgs]
        res_active = []
        for active_org in active_orgs:
            org_uid = active_org.UID()
            res_active.append(SimpleTerm(org_uid, org_uid, safe_unicode(active_org.get_full_title(first_index=1))))
        res = humansorted(res_active, key=attrgetter("title"))

        res_not_active = []
        for not_active_org in not_active_orgs:
            org_uid = not_active_org.UID()
            res_not_active.append(
                SimpleTerm(
                    org_uid,
                    org_uid,
                    _tr(
                        "${element_title} (Inactive)",
                        mapping={"element_title": safe_unicode(not_active_org.get_full_title(first_index=1))},
                    ),
                )
            )
        res = res + humansorted(res_not_active, key=attrgetter("title"))
        return SimpleVocabulary(res)

    __call__ = TreatingGroupsWithDeactivatedVocabulary__call__


@implementer(IVocabularyFactory)
class TreatingGroupsForFacetedFilterVocabulary(object):
    """Will be used in faceted criteria with deactivated orgs at the end."""

    @ram.cache(voc_cache_key)
    def TreatingGroupsForFacetedFilterVocabulary__call__(self, context):
        factory = getUtility(IVocabularyFactory, "imio.dms.mail.TreatingGroupsWithDeactivatedVocabulary")
        vocab = factory(context)
        hidden_orgs = (
            api.portal.get_registry_record(
                "imio.dms.mail.browser.settings.IImioDmsMailConfig.groups_hidden_in_dashboard_filter", default=[]
            )
            or []
        )
        return SimpleVocabulary([term for term in vocab._terms if term.value not in hidden_orgs])

    __call__ = TreatingGroupsForFacetedFilterVocabulary__call__


class DmsPrimaryOrganizationsVocabulary(PrimaryOrganizationsVocabulary):
    def __call__(self, context, userid=None):
        """ """
        return super(DmsPrimaryOrganizationsVocabulary, self).__call__(
            context,
            userid=userid,
            suffixes=ALL_SERVICE_FUNCTIONS,
            base_voc="collective.dms.basecontent.treating_groups",
        )


@implementer(IVocabularyFactory)
class ActiveInactiveStatesVocabulary(object):
    """States of active_inactive_workflow"""

    def __call__(self, context):
        return SimpleVocabulary(
            [SimpleTerm("active", title=pmf(u"Active")), SimpleTerm("deactivated", title=pmf(u"Deactivated"))]
        )


@implementer(IVocabularyFactory)
class DmsFilesCategoryVocabulary(CategoryVocabulary):
    """Vocabulary to retrieve available content categories for incoming mails, outgoing mails and
    classification folders"""

    def _get_categories(self, context, only_enabled=True):
        catalog = api.portal.get_tool('portal_catalog')
        parent_type = context.aq_parent.portal_type
        context_type = context.portal_type
        url = context.REQUEST.getURL()
        typeupload = context.REQUEST.get('typeupload', '')
        query = {
            "object_provides": "collective.iconifiedcategory.content.category.ICategory",
            "enabled": True,
            "path": [],
        }
        portal_path = "/".join(api.portal.get().getPhysicalPath())
        if {"dmsincomingmail", "dmsincoming_email"}.intersection({parent_type, context_type}):
            if context_type == "dmsmainfile" or url.endswith("dmsmainfile"):
                query["path"] = "{}/annexes_types/incoming_dms_files".format(portal_path)
            elif (context_type == 'dmsappendixfile' or url.endswith('dmsappendixfile')
                  or typeupload == 'dmsappendixfile'):
                query["path"] = "{}/annexes_types/incoming_appendix_files".format(portal_path)
        elif {"dmsoutgoingmail", "dmsoutgoing_email"}.intersection({parent_type, context_type}):
            if context_type == "dmsommainfile" or url.endswith("dmsommainfile"):
                query["path"] = "{}/annexes_types/outgoing_dms_files".format(portal_path)
            elif (context_type == "dmsappendixfile" or url.endswith("dmsappendixfile")
                  or typeupload == 'dmsappendixfile'):
                query["path"] = "{}/annexes_types/outgoing_appendix_files".format(portal_path)
        elif {"sign_request"}.intersection({parent_type, context_type}):
            query["path"] = "{}/annexes_types/sign_request_appendix_files".format(portal_path)
        elif {"ClassificationFolder", "ClassificationSubfolder", "annex"}.intersection({parent_type, context_type}):
            query["path"] = "{}/annexes_types/annexes".format(portal_path)
        else:
            return super(DmsFilesCategoryVocabulary, self)._get_categories(context, only_enabled)

        return [b.getObject() for b in catalog.unrestrictedSearchResults(**query)]


@implementer(IVocabularyFactory)
class PODTemplateContentCategoriesVocabulary(object):
    """Return content categories vocabulary for POD templates."""

    def __call__(self, context):
        catalog = api.portal.get_tool('portal_catalog')
        portal_path = '/'.join(api.portal.get().getPhysicalPath())
        query = {
            'object_provides': 'collective.iconifiedcategory.content.category.ICategory',
            'enabled': True,
            'path': ['{}/annexes_types/outgoing_dms_files'.format(portal_path)],
        }
        brains = catalog.unrestrictedSearchResults(**query)
        content_categories = [(calculate_category_id(b.getObject()), b.Title) for b in brains]
        return SimpleVocabulary([SimpleTerm(value=cc, token=cc, title=tit) for cc, tit in content_categories])
