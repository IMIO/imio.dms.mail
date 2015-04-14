# -*- coding: utf-8 -*-
"""Vocabularies."""
from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm

from eea.faceted.vocabularies.utils import IVocabularyFactory

from collective.contact.facetednav import _


class ContactPortalTypesVocabulary(object):
    """Vocabulary factory for contact portal types."""
    implements(IVocabularyFactory)

    def __call__(self, context):
        context = getattr(context, 'context', context)
        items = [(_(u"Organizations"), 'organization'),
                 # (_(u"Contacts"), 'held_position'),
                 (_(u"Persons"), 'person')]
        items = [SimpleTerm(i[1], i[1], i[0]) for i in items]
        return SimpleVocabulary(items)

ContactPortalTypesVocabularyFactory = ContactPortalTypesVocabulary()
