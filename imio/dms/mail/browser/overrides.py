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


class IMRenderCategoryView(RenderCategoryView):
    '''
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items or meetings.
    '''

    def __call__(self, widget):
        self.widget = widget

        return ViewPageTemplateFile("templates/category_im.pt")(self)


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
