# -*- coding: utf-8 -*-
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from collective.contact.core.content.directory import IDirectory


class IDirectoryFacetedNavigable(IFacetedNavigable, IDirectory):

    """Marker interface for contacts directory."""
