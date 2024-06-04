# -*- coding: utf-8 -*-

from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from imio.actionspanel.interfaces import IActionsPanelLayer
from plone.dexterity.interfaces import IDexterityContainer
from plone.theme.interfaces import IDefaultPloneLayer
from zope.interface import Interface


class IImioDmsIncomingMailWfConditions(Interface):
    """Adapter interface adding methods used in im workflow conditions"""


class IImioDmsOutgoingMailWfConditions(Interface):
    """Adapter interface adding methods used in om workflow conditions"""


class IImioDmsMailLayer(IDefaultPloneLayer, IActionsPanelLayer):
    """Marker interface that defines a Zope 3 browser layer."""


class IDocsDashboard(Interface):

    """Marker interface for all ia.docs dashboards."""


class IIMDashboard(IDocsDashboard):

    """Marker interface for incoming mail dashboard."""


class IIMDashboardBatchActions(IIMDashboard, IBatchActionsMarker):

    """Marker interface for incoming mail dashboard with batch actions."""


class IOMDashboard(IDocsDashboard):

    """Marker interface for outgoing mail dashboard."""


class IOMDashboardBatchActions(IOMDashboard, IBatchActionsMarker):

    """Marker interface for outgoing mail dashboard with batch actions."""


class ITaskDashboard(IDocsDashboard):

    """Marker interface for task dashboard."""


class ITaskDashboardBatchActions(ITaskDashboard, IBatchActionsMarker):

    """Marker interface for task dashboard with batch actions."""


# class IContactsDashboard(IDocsDashboard):  #interference with current bacth actions
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


class IClassificationFoldersDashboard(IDocsDashboard):

    """Marker interface for folders dashboard."""


class IClassificationFoldersDashboardBatchActions(IClassificationFoldersDashboard, IBatchActionsMarker):

    """Marker interface for folders dashboard with batch actions."""


class IActionsPanelFolder(Interface):

    """Marker interface for folder displaying actions panel viewlet, without transitions."""


class IActionsPanelFolderAll(Interface):

    """Marker interface for folder displaying actions panel viewlet, with transitions."""


class IActionsPanelFolderOnlyAdd(Interface):

    """Marker interface for folder displaying actions panel viewlet, without transitions and actions."""


class IOMTemplatesFolder(IBatchActionsMarker):

    """Marker interface for folder displaying dg-templates-listing"""


class IOMCKTemplatesFolder(IBatchActionsMarker):

    """Marker interface for folder displaying ck-templates-listing"""


class IPersonnelContact(Interface):
    """
    Marker interface for personnel contacts.
    """


class IPersonnelFolder(Interface):

    """Marker interface for folder displaying personnel-listing"""


class IMemberAreaFolder(IDexterityContainer):
    """
    Marker interface for member area folder.
    """


class IProtectedItem(Interface):
    """Marker interface to protect object against deletion, cut and rename"""
