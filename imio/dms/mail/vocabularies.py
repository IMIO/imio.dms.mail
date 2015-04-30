# -*- coding: utf-8 -*-
"""Vocabularies."""
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from plone import api

from collective.contact.core.content.person import IPerson
from collective.contact.core.content.held_position import IHeldPosition

from imio.dms.mail.interfaces import IInternalOrganization, IExternalOrganization


class InterfacesShownInFacetedNav(object):

    """List interfaces that will be shown in faceted navigation."""

    def __call__(self, context):
        interfaces = [
            IExternalOrganization,
            IInternalOrganization,
            IPerson,
            IHeldPosition
            ]

        terms = [SimpleVocabulary.createTerm(
                    interface.__identifier__,
                    interface.__identifier__,
                    interface.__name__)
                 for interface in interfaces]

        return SimpleVocabulary(terms)
