# -*- coding: utf-8 -*-
"""Vocabularies."""
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleVocabulary
from plone.memoize.instance import memoize
from imio.dms.mail.interfaces import IInternalContact, IExternalContact
from imio.dms.mail.utils import list_wf_states


class IMReviewStatesVocabulary(object):
    """ Incoming mail states vocabulary """
    implements(IVocabularyFactory)

    @memoize
    def __call__(self, context):
        terms = []
        for state in list_wf_states(context, 'dmsincomingmail'):
            terms.append(SimpleVocabulary.createTerm(
                state, state, translate(state, domain='plone', context=context.REQUEST)))

        return SimpleVocabulary(terms)


class InterfacesShownInFacetedNav(object):
    """List interfaces that will be shown in contacts faceted navigation."""
    implements(IVocabularyFactory)

    def __call__(self, context):
        interfaces = [
            IExternalContact,
            IInternalContact,
        ]

        terms = [SimpleVocabulary.createTerm(
            interface.__identifier__,
            interface.__identifier__,
            interface.__name__)
            for interface in interfaces]

        return SimpleVocabulary(terms)
