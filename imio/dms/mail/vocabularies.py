# -*- coding: utf-8 -*-
"""Vocabularies."""
from zope.component import getUtility, queryUtility
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from plone.i18n.normalizer.interfaces import IIDNormalizer
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from collective.contact.plonegroup.config import ORGANIZATIONS_REGISTRY
from collective.contact.plonegroup.interfaces import IPloneGroupContact, INotPloneGroupContact
from imio.dms.mail.utils import list_wf_states, get_selected_org_suffix_users
from imio.helpers.cache import get_cachekey_volatile
from browser.settings import IImioDmsMailConfig
from . import _


def voc_cache_key(method, self, context):
    return get_cachekey_volatile("%s.%s" % (self.__class__.__module__, self.__class__.__name__))


class IMReviewStatesVocabulary(object):
    """ Incoming mail states vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        terms = []
        for state in list_wf_states(context, 'dmsincomingmail'):
            terms.append(SimpleVocabulary.createTerm(
                state, state, translate(state, domain='plone', context=context.REQUEST)))
        return SimpleVocabulary(terms)


class TaskReviewStatesVocabulary(object):
    """ Task states vocabulary """
    implements(IVocabularyFactory)

    @ram.cache(voc_cache_key)
    def __call__(self, context):
        terms = []
        for state in list_wf_states(context, 'task'):
            terms.append(SimpleVocabulary.createTerm(
                state, state, translate(state, domain='plone', context=context.REQUEST)))
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
            members = get_selected_org_suffix_users(uid, ['editeur', 'validateur'])
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


def getMailTypes(choose=False, active=[True, False]):
    """
        Create a vocabulary from registry mail_types variable
    """
    settings = getUtility(IRegistry).forInterface(IImioDmsMailConfig, False)
    terms = []
    if choose:
        terms.append(SimpleVocabulary.createTerm(None, '', _("Choose a value !")))
    id_utility = queryUtility(IIDNormalizer)
    for mail_type in settings.mail_types:
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
        ]

        terms = [SimpleVocabulary.createTerm(
            interface.__identifier__,
            interface.__identifier__,
            interface.__name__)
            for interface in interfaces]

        return SimpleVocabulary(terms)
