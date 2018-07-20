# -*- coding: utf-8 -*-

from collective.contact.core.content.directory import IDirectory
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from eea.facetednavigation.subtypes.interfaces import IFacetedNavigable
from plone.dexterity.interfaces import IDexterityContainer
from zope.interface import Interface


class IDirectoryFacetedNavigable(IFacetedNavigable, IDirectory):

    """Marker interface for contacts directory. MUST BE REMOVED in next version"""


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


#class IContactsDashboard(IDocsDashboard):  #interference with current bacth actions
class IContactsDashboard(Interface):

    """Marker interface for contacts dashboard."""


class IOrganizationsDashboard(IContactsDashboard):

    """Marker interface for organisations dashboard."""


class IOrganizationsDashboardBatchActions(IOrganizationsDashboard, IBatchActionsMarker):

    """Marker interface for organisations dashboard with batch actions."""


class IPersonsDashboard(IContactsDashboard):

    """Marker interface for persons dashboard."""


class IPersonsDashboardBatchActions(IPersonsDashboard, IBatchActionsMarker):

    """Marker interface for persons dashboard with batch actions."""


class IHeldPositionsDashboard(IContactsDashboard):

    """Marker interface for held positions dashboard."""


class IHeldPositionsDashboardBatchActions(IHeldPositionsDashboard, IBatchActionsMarker):

    """Marker interface for held positions dashboard with batch actions."""


class IContactListsDashboard(IContactsDashboard):

    """Marker interface for contact lists dashboard."""


class IContactListsDashboardBatchActions(IContactListsDashboard, IBatchActionsMarker):

    """Marker interface for contact lists dashboard with batch actions."""


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
