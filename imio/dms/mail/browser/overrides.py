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
from collective.eeafaceted.z3ctable.columns import VocabularyColumn, MemberIdColumn
from imio.dashboard.browser.overrides import IDFacetedTableView


class FolderFacetedTableView(IDFacetedTableView):
    """ Override of faceted-table-view for Folder (incomingmail) """

    def _manualColumnFor(self, colName):
        """Manage our own columns."""
        if colName == u'treating_groups':
            column = VocabularyColumn(self.context, self.request, self)
            column.vocabulary = u'collective.dms.basecontent.treating_groups'
        elif colName == u'assigned_user':
            column = MemberIdColumn(self.context, self.request, self)
            column.attrName = u'assigned_user'
        else:
            column = super(FolderFacetedTableView, self)._manualColumnFor(colName)

        return column


class IMRenderCategoryView(RenderCategoryView):
    '''
      Override the way a category is rendered in the portlet based on the
      faceted collection widget so we can manage some usecases where icons
      are displayed to add items or meetings.
    '''

    def __call__(self, category, widget):
        self.category = category
        self.widget = widget

        if category[0] == 'collections':
            return ViewPageTemplateFile("templates/category_im.pt")(self)
        else:
            return self.index()

