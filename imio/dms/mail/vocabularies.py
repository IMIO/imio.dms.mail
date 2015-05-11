# -*- coding: utf-8 -*-
"""Vocabularies."""
from zope.schema.vocabulary import SimpleVocabulary

from imio.dms.mail.interfaces import IInternalContact, IExternalContact


class InterfacesShownInFacetedNav(object):

    """List interfaces that will be shown in faceted navigation."""

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
