# -*- coding: utf-8 -*-
"""Vocabularies."""
from zope.component import getUtility, queryUtility
from zope.i18n import translate
from zope.interface import implements, alsoProvides
from zope.schema.interfaces import IVocabularyFactory, IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from plone import api
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.interfaces import IPloneGroupContact, INotPloneGroupContact
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.utils import list_wf_states, get_selected_org_suffix_users, organizations_with_suffixes
from imio.helpers.cache import get_cachekey_volatile
from browser.settings import IImioDmsMailConfig
from . import _, EMPTY_STRING


def voc_cache_key(method, self, context):
    return get_cachekey_volatile("%s.%s" % (self.__class__.__module__, self.__class__.__name__))


class IMReviewStatesVocabulary(object):
    """ Incoming mail states vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        tl = api.portal.get().portal_properties.site_properties.getProperty('default_language', 'fr')
        for state in list_wf_states(context, 'dmsincomingmail'):
            terms.append(SimpleVocabulary.createTerm(
                state.id, state.id, translate(state.title, domain='plone', target_language=tl)))
        return SimpleVocabulary(terms)


class OMReviewStatesVocabulary(object):
    """ Outgoing mail states vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        tl = api.portal.get().portal_properties.site_properties.getProperty('default_language', 'fr')
        for state in list_wf_states(context, 'dmsoutgoingmail'):
            terms.append(SimpleVocabulary.createTerm(
                state.id, state.id, translate(state.title, domain='plone', target_language=tl)))
        return SimpleVocabulary(terms)


class TaskReviewStatesVocabulary(object):
    """ Task states vocabulary """
    implements(IVocabularyFactory)

    def __call__(self, context):
        terms = []
        for state in list_wf_states(context, 'task'):
            terms.append(SimpleVocabulary.createTerm(
                state.id, state.id, translate(state.title, domain='plone', context=context.REQUEST)))
        return SimpleVocabulary(terms)


class AssignedUsersVocabulary(object):
    """ All possible assigned users vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        registry = getUtility(IRegistry)
        terms = []
        users = {}
        titles = []
        for uid in registry[ORGANIZATIONS_REGISTRY]:
            members = get_selected_org_suffix_users(uid, ['editeur', 'encodeur', 'validateur'])
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


def getMailTypes(choose=False, active=[True, False], field='mail_types'):
    """
        Create a vocabulary from registry mail_types variable
    """
    settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
    terms = []
    if choose:
        terms.append(SimpleVocabulary.createTerm(None, '', _("Choose a value !")))
    id_utility = queryUtility(IIDNormalizer)
    for mail_type in getattr(settings, field) or []:
        #value (stored), token (request), title
        if mail_type['mt_active'] in active:
            terms.append(SimpleVocabulary.createTerm(mail_type['mt_value'],
                         id_utility.normalize(mail_type['mt_value']), mail_type['mt_title']))
    return SimpleVocabulary(terms)


class IMMailTypesVocabulary(object):
    """ Mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return getMailTypes()


class IMActiveMailTypesVocabulary(object):
    """ Active mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return getMailTypes(choose=True, active=[True])


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
    """ Outgoing mail sender vocabulary """
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
            hp = brain.getObject()
            person = hp.get_person()
            terms.append((person, hp,
                          SimpleVocabulary.createTerm(brain.UID, "%s_%s" % (brain.UID, brain.mail_type or ''),
                                                      brain.getObject().get_full_title(first_index=1))))

        def sort_terms(t):
            return getattr(t[0], sort_on[0]), getattr(t[0], sort_on[1]), t[1].get_full_title(first_index=1)

        return SimpleVocabulary([term for pers, hp, term in sorted(terms, key=sort_terms)])


class OMMailTypesVocabulary(object):
    """ Mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return getMailTypes(field='omail_types')


class OMActiveMailTypesVocabulary(object):
    """ Active mail types vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        return getMailTypes(active=[True], field='omail_types')


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
        orgs = organizations_with_suffixes(api.group.get_groups(user=current_user), ['encodeur', 'validateur'])
        return SimpleVocabulary([term for term in voc.vocab._terms if term.value in orgs])
    return voc

alsoProvides(encodeur_active_orgs, IContextSourceBinder)
