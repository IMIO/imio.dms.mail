# -*- coding: utf-8 -*-
"""Vocabularies."""
from browser.settings import IImioDmsMailConfig
from collective.contact.plonegroup.config import get_registry_organizations
from collective.contact.plonegroup.interfaces import INotPloneGroupContact
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_selected_org_suffix_users
from collective.contact.plonegroup.utils import organizations_with_suffixes
from ftw.labels.interfaces import ILabelJar
from imio.dms.mail import _
from imio.dms.mail import ALL_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail import CREATING_GROUP_SUFFIX
from imio.dms.mail import EMPTY_STRING
from imio.dms.mail import OM_EDITOR_SERVICE_FUNCTIONS
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.utils import list_wf_states
from imio.helpers.cache import get_cachekey_volatile
from plone import api
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.utils import base_hasattr
from Products.CMFPlone.utils import safe_unicode
from unidecode import unidecode  # unidecode_expect_nonascii not yet available in used version
from z3c.formwidget.query.interfaces import IQuerySource
from zope.component import getUtility
from zope.component import queryUtility
from zope.i18n import translate
from zope.interface import alsoProvides
from zope.interface import implements
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary

import re


def voc_cache_key(method, self, context):
    return get_cachekey_volatile("%s.%s" % (self.__class__.__module__, self.__class__.__name__))


class IMReviewStatesVocabulary(object):
    """ Incoming mail states vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        tl = api.portal.get().portal_properties.site_properties.getProperty('default_language', 'fr')
        for state in list_wf_states(context, 'dmsincomingmail'):  # i_e ok
            terms.append(SimpleVocabulary.createTerm(
                state.id, state.id, translate(safe_unicode(state.title), domain='plone', target_language=tl)))
        return SimpleVocabulary(terms)


class OMReviewStatesVocabulary(object):
    """ Outgoing mail states vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        tl = api.portal.get().portal_properties.site_properties.getProperty('default_language', 'fr')
        for state in list_wf_states(context, 'dmsoutgoingmail'):
            terms.append(SimpleVocabulary.createTerm(
                state.id, state.id, translate(safe_unicode(state.title), domain='plone', target_language=tl)))
        return SimpleVocabulary(terms)


class TaskReviewStatesVocabulary(object):
    """ Task states vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        for state in list_wf_states(context, 'task'):
            terms.append(SimpleVocabulary.createTerm(
                state.id, state.id, translate(safe_unicode(state.title), domain='plone', context=context.REQUEST)))
        return SimpleVocabulary(terms)


class ContactsReviewStatesVocabulary(object):
    """ Contacts states vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        for state in list_wf_states(context, 'organization'):
            terms.append(SimpleVocabulary.createTerm(
                state.id, state.id, translate(safe_unicode(state.title), domain='plone', context=context.REQUEST)))
        return SimpleVocabulary(terms)


class AssignedUsersVocabulary(object):
    """ All possible assigned users vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        terms = []
        users = {}
        titles = []
        for uid in get_registry_organizations():
            members = get_selected_org_suffix_users(uid, ALL_EDITOR_SERVICE_FUNCTIONS)
            for member in members:
                title = member.getUser().getProperty('fullname') or member.getUserName()
                if title not in titles:
                    titles.append(title)
                    users[title] = [member]
                elif member not in users[title]:
                    users[title].append(member)
        for tit in sorted(titles):
            for mb in users[tit]:
                terms.append(SimpleTerm(mb.getUserName(), mb.getId(), tit))
        return SimpleVocabulary(terms)


class EmptyAssignedUsersVocabulary(object):
    """ All possible assigned users vocabulary with empty value """
    implements(IVocabularyFactory)

    def __call__(self, context):
        voc_inst = AssignedUsersVocabulary()
        voc = voc_inst(context)
        terms = [SimpleTerm(EMPTY_STRING, EMPTY_STRING, _('Empty value'))]
        for term in voc:
            terms.append(term)
        return SimpleVocabulary(terms)


def get_settings_vta_table(field, active=(True, False), choose=False):
    """
        Create a vocabulary from registry table variable (value, title, active)
    """
    settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
    terms = []
    id_utility = queryUtility(IIDNormalizer)
    for mail_type in (getattr(settings, field) or []):
        # value (stored), token (request), title
        if mail_type['active'] in active:
            val = mail_type['value']
            if val == 'None':
                val = None
                choose = False
            terms.append(SimpleTerm(val, id_utility.normalize(mail_type['value']), mail_type['dtitle']))
    if choose:
        terms.insert(0, SimpleTerm(None, '', _("Choose a value !")))
    return SimpleVocabulary(terms)


class IMMailTypesVocabulary(object):
    """ Mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return get_settings_vta_table('mail_types')


class IMActiveMailTypesVocabulary(object):
    """ Active mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return get_settings_vta_table('mail_types', choose=True, active=[True])


class PloneGroupInterfacesVocabulary(object):
    """List interfaces that will be shown in contacts faceted navigation."""
    implements(IVocabularyFactory)

    def __call__(self, context):
        interfaces = [
            IPloneGroupContact,
            INotPloneGroupContact,
            IPersonnelContact
        ]

        terms = [SimpleVocabulary.createTerm(
            interface.__identifier__,
            interface.__identifier__,
            interface.__name__)
            for interface in interfaces]

        return SimpleVocabulary(terms)


class OMSenderVocabulary(object):
    """
        Outgoing mail sender vocabulary
        term value = hp uid
        term token = org uid _ userid
        term title = hp title
    """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        catalog = api.portal.get_tool('portal_catalog')
        sfs = api.portal.get_registry_record('imio.dms.mail.browser.settings.IImioDmsMailConfig.'
                                             'omail_sender_firstname_sorting')
        sort_on = ['firstname', 'lastname']
        sfs or sort_on.reverse()

        brains = catalog.unrestrictedSearchResults(
            portal_type=['held_position'],
            object_provides='imio.dms.mail.interfaces.IPersonnelContact',
            review_state='active')

        terms = []
        for brain in brains:
            # the userid is stored in mail_type index !!
            hp = brain._unrestrictedGetObject()
            person = hp.get_person()
            org = hp.get_organization()
            terms.append((person, hp,
                          SimpleVocabulary.createTerm(
                              brain.UID, '{}_{}_{}'.format(brain.UID, org.UID(), brain.mail_type or ''),
                              hp.get_full_title(first_index=1))))

        def sort_terms(t):
            return getattr(t[0], sort_on[0]), getattr(t[0], sort_on[1]), t[1].get_full_title(first_index=1)

        return SimpleVocabulary([term for pers, hpo, term in sorted(terms, key=sort_terms)])


class OMMailTypesVocabulary(object):
    """ Mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return get_settings_vta_table('omail_types')


class OMActiveMailTypesVocabulary(object):
    """ Active mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return get_settings_vta_table('omail_types', active=[True])


class OMActiveSendModesVocabulary(object):
    """ Active send modes vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return get_settings_vta_table('omail_send_modes', active=[True])


def encodeur_active_orgs(context):
    current_user = api.user.get_current()
    factory = getUtility(IVocabularyFactory, u'collective.dms.basecontent.treating_groups')
    voc = factory(context)
    # this is the case when calling ++widget++...
    if current_user.getId() is None:
        return voc
    # the expedition group must have all values
    if 'expedition' in [g.id for g in api.group.get_groups(user=current_user)]:
        return voc
    # we filter orgs if
    #   * current user is not admin
    #   * portal_type is not dmsoutgoingmail (on adding or reply)
    #   * state is created
    if (not current_user.has_role(['Manager', 'Site Administrator']) and
            (context.portal_type != 'dmsoutgoingmail' or api.content.get_state(context) == 'created')):
        orgs = organizations_with_suffixes(api.group.get_groups(user=current_user), OM_EDITOR_SERVICE_FUNCTIONS)
        return SimpleVocabulary([term for term in voc.vocab._terms if term.value in orgs])
    return voc


alsoProvides(encodeur_active_orgs, IContextSourceBinder)


class LabelsVocabulary(object):
    """ Labels vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        try:
            adapted = ILabelJar(context)
        except:  # noqa
            return SimpleVocabulary(terms)
        user = api.user.get_current()
        for label in adapted.list():
            if label['by_user']:
                terms.append(SimpleVocabulary.createTerm('%s:%s' % (user.id, label['label_id']),
                                                         '%s_%s' % (user.id, label['label_id']),
                                                         safe_unicode(label['title'])))
            else:
                terms.append(SimpleVocabulary.createTerm(label['label_id'], label['label_id'],
                                                         safe_unicode(label['title'])))
        return SimpleVocabulary(terms)


class CreatingGroupVocabulary(object):
    """ Creating group vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        terms = []
        factory = getUtility(IVocabularyFactory, 'collective.contact.plonegroup.organization_services')
        vocab = factory(context)

        # we get all orgs where there are plone groups with the creating group suffix
        to_keep = organizations_with_suffixes(api.group.get_groups(), [CREATING_GROUP_SUFFIX])
        for term in vocab:
            if term.value in to_keep:
                terms.append(term)
        return SimpleVocabulary(terms)


class ActiveCreatingGroupVocabulary(object):
    """ Active creating group vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        terms = []
        factory = getUtility(IVocabularyFactory, 'collective.contact.plonegroup.organization_services')
        vocab = factory(context)

        # we get all orgs where there are plone groups with the creating group suffix and with users
        to_keep = get_organizations(not_empty_suffix=CREATING_GROUP_SUFFIX, only_selected=False, the_objects=False,
                                    caching=False)
        for term in vocab:
            if term.value in to_keep:
                terms.append(term)
        return SimpleVocabulary(terms)


class SourceAbleVocabulary(object):
    implements(IQuerySource)

    vocabulary_name = ''
    vocabulary = None

    def __init__(self, context):
        self.context = context
        if self.vocabulary_name:
            voc_inst = getUtility(IVocabularyFactory, self.vocabulary_name)
            self.vocabulary = voc_inst(self.context)
        self.__contains__ = self.vocabulary.__contains__
        self.getTerm = self.vocabulary.getTerm
        self.getTermByToken = self.vocabulary.getTermByToken
        if base_hasattr(self.vocabulary, 'flattened_titles'):
            self.flattened_titles = self.vocabulary.flattened_titles
        else:
            self.decoded_titles()

    def __iter__(self):
        for term in self.vocabulary._terms:
            yield term

    def decoded_titles(self):
        self.flattened_titles = {}
        for term in self.vocabulary._terms:
            self.flattened_titles[term.value] = ''.join(['|%s' % p for p in re.findall(r"\w+",
                                                        unidecode(safe_unicode(term.title)).lower()) if len(p) > 1])

    def search(self, query_string):
        searched = ['|%s' % unidecode(safe_unicode(p)).lower() for p in query_string.split(' ')]
        return [t for t in self.vocabulary._terms if all([s in self.flattened_titles[t.value] for s in searched])]


class SourceAbleContextBinder(object):
    implements(IContextSourceBinder)
    source_class = None

    def __call__(self, context):
        return self.source_class(context)


class ServicesSourceAbleVocabulary(SourceAbleVocabulary):
    vocabulary_name = u'collective.dms.basecontent.recipient_groups'


class ServicesSourceBinder(SourceAbleContextBinder):
    source_class = ServicesSourceAbleVocabulary


class ActionCategoriesVocabularyFactory(object):
    """Provides an actions categories vocabulary"""
    implements(IVocabularyFactory)

    def __call__(self, context):
        portal_actions = api.portal.get_tool('portal_actions')

        categories = portal_actions.objectIds()
        categories.sort()
        return SimpleVocabulary(
            [SimpleTerm(cat, title=cat) for cat in categories]
        )
