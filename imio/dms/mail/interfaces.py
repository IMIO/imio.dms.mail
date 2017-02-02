# -*- coding: utf-8 -*-
from zope.interface import Interface

from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from collective.contact.core.content.directory import IDirectory


class IDirectoryFacetedNavigable(IFacetedNavigable, IDirectory):

    """Marker interface for contacts directory."""


class IExternalContact(Interface):

    """Marker interface for external organizations."""


class IInternalContact(Interface):

    """Marker interface for internal organizations

    i.e. organizations in plonegroup-organization."""


class IDocsDashboard(Interface):

    """Marker interface for all ia.docs dashboards."""


class IIMDashboard(IDocsDashboard):

    """Marker interface for incoming mail dashboard."""


class IOMDashboard(IDocsDashboard):

    """Marker interface for outgoing mail dashboard."""


class IIMTaskDashboard(Interface):

    """TO BE REMOVED RELEASE > 2.0"""


class ITaskDashboard(IDocsDashboard):

    """Marker interface for task dashboard."""
