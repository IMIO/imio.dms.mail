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


class IMRenderCategoryView(RenderCategoryView):
    '''
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items or meetings.
    '''

    def __call__(self, widget):
        self.widget = widget

        if self.context.getId() == 'collections':
            return ViewPageTemplateFile("templates/category_im.pt")(self)
        else:
            return self.index()

