# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.eeafaceted.collectionwidget.browser.views import RenderCategoryView
from imio.history.browser.views import IHDocumentBylineViewlet
from plone import api
from plone.locking.browser.info import LockInfoViewlet as PLLockInfoViewlet
from plone.locking.browser.locking import LockingOperations as PLLockingOperations

from ..interfaces import IIMDashboard, IOMDashboard


class IMRenderCategoryView(RenderCategoryView):
    '''
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items or meetings.
    '''

    def __call__(self, widget):
        self.widget = widget
        if IIMDashboard.providedBy(self.context):
            return ViewPageTemplateFile("templates/category_im.pt")(self)
        if IOMDashboard.providedBy(self.context):
            return ViewPageTemplateFile("templates/category_om.pt")(self)
        return ViewPageTemplateFile("templates/category.pt")(self)


class DocumentBylineViewlet(IHDocumentBylineViewlet):
    '''
      Overrides the IHDocumentBylineViewlet to hide it for some layouts.
    '''

    def show(self):
        currentLayout = self.context.getLayout()
        if currentLayout in ['facetednavigation_view', ]:
            return False
        return True

    def creator(self):
        if self.context.portal_type == 'dmsincomingmail':
            return None
        return super(DocumentBylineViewlet, self).creator()


class LockInfoViewlet(PLLockInfoViewlet):

    def lock_is_stealable(self):
        if self.context.portal_type in api.portal.get_registry_record('externaleditor.externaleditor_enabled_types',
                                                                      default=[]):
            return True
        return super(LockInfoViewlet, self).lock_is_stealable()


class LockingOperations(PLLockingOperations):

    def force_unlock(self, redirect=True):
        """ Can unlock external edit lock """
        if self.context.portal_type in api.portal.get_registry_record('externaleditor.externaleditor_enabled_types',
                                                                      default=[]):
            self.context.wl_clearLocks()
            self.request.RESPONSE.redirect('%s/view' % self.context.absolute_url())
        else:
            super(LockingOperations, self).force_unlock(redirect=redirect)
