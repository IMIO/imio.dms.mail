# -*- coding: utf-8 -*-

from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from collective.contact.core.content.directory import IDirectory
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from plone.dexterity.interfaces import IDexterityContainer
from zope.interface import Interface


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


class ITaskDashboard(IDocsDashboard):

    """Marker interface for task dashboard."""


class IActionsPanelFolder(Interface):

    """Marker interface for folder displaying actions panel viewlet."""


class IActionsPanelFolderAll(Interface):

    """Marker interface for folder displaying actions panel viewlet."""


class IOMTemplatesFolder(IBatchActionsMarker):

    """Marker interface for folder displaying dg-templates-listing"""


class IPersonnelContact(Interface):
    """
        Marker interface for personnel contacts.
    """


class IMemberAreaFolder(IDexterityContainer):
    """
        Marker interface for member area folder.
    """


class IContactListFolder(Interface):
    """
        Marker interface for contact_list folder.
    """
