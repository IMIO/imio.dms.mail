# -*- coding: utf-8 -*-
from zope.interface import Interface

from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from collective.contact.core.content.directory import IDirectory


class IDirectoryFacetedNavigable(IFacetedNavigable, IDirectory):

    """Marker interface for contacts directory."""


class IExternalOrganization(Interface):

    """Marker interface for external organizations."""


class IInternalOrganization(Interface):

    """Marker interface for internal organizations

    i.e. organizations in plonegroup-organization."""
