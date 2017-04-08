# -*- coding: utf-8 -*-
from zope.i18n import translate

import json
from zope.interface import implements

from Products.CMFPlone.browser.ploneview import Plone
from Products.Five import BrowserView
from plone import api
from plone.app.contenttypes.interfaces import IFile

from imio.helpers.fancytree.views import BaseRenderFancyTree
from eea.faceted.vocabularies.autocomplete import IAutocompleteSuggest

from imio.dms.mail import _
from ..setuphandlers import _ as _fr


class PloneView(Plone):
    """
        Redefinition of plone view
    """

    def showEditableBorder(self):
        """Determine if the editable border (green bar) should be shown
        """
        return True


class CreateFromTemplateForm(BaseRenderFancyTree):

    """Create a document from a collective.documentgenerator template."""

    def label(self):
        return translate(
            _(u"${title}: create from template",
              mapping={'title': self.context.Title()}),
            context=self.request)

    def get_action_name(self):
        return translate(_("Choose this template"), context=self.request)

    def get_query(self):
        portal = api.portal.get()
        path = '/'.join(portal.getPhysicalPath()) + '/models'
        return {
            'path': {'query': path, 'depth': -1},
            'portal_type': (
                'Folder',
                'ConfigurablePODTemplate',
                'PODTemplate',
                'StyleTemplate',
                # 'SubTemplate',
            ),
        }

    def redirect_url(self, uid):
        """Redirect to document generation from selected template."""
        url = self.context.absolute_url()
        params = [
            "template_uid={}".format(uid),
            "output_format=odt",
        ]
        return "{}/document-generation?{}".format(url, "&".join(params))


def parse_query(text):
    """ Copied from plone.app.vocabularies.catalog.parse_query but cleaned.
    """
    for char in '?-+*()':
        text = text.replace(char, ' ')
    query = {'SearchableText': " AND ".join(x + "*" for x in text.split())}
    return query


class ContactSuggest(BrowserView):
    """ Contact Autocomplete view """
    implements(IAutocompleteSuggest)

    label = u"Contact"

    def __call__(self):
        result = []
        query = self.request.get('term')
        if not query:
            return json.dumps(result)

        self.request.response.setHeader("Content-type", "application/json")
        query = parse_query(query)
        hp, org_bis = [], []
        all_str = _fr('All under')
        # search held_positions
        crit = {'portal_type': 'held_position', 'sort_on': 'sortable_title'}
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        for brain in brains:
            hp.append({'id': brain.UID, 'text': brain.get_full_title})
        # search organizations
        crit = {'portal_type': ('organization'), 'sort_on': 'sortable_title'}
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        make_bis = (len(hp) + len(brains)) > 1 and True or False
        for brain in brains:
            result.append({'id': brain.UID, 'text': brain.get_full_title})
            if make_bis:
                org_bis.append({'id': 'l:%s' % brain.UID, 'text': '%s [%s]' % (brain.get_full_title, all_str)})
        result += hp
        # search persons
        crit = {'portal_type': ('person'), 'sort_on': 'sortable_title'}
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        for brain in brains:
            result.append({'id': brain.UID, 'text': brain.get_full_title})
        # add organizations bis
        result += org_bis
        return json.dumps(result)


class SenderSuggest(BrowserView):
    """ Contact Autocomplete view """
    implements(IAutocompleteSuggest)

    label = u"Sender"

    def __call__(self):
        result = []
        query = self.request.get('term')
        if not query:
            return json.dumps(result)
        self.request.response.setHeader("Content-type", "application/json")
        query = parse_query(query)
        hp, org_bis = [], []
        all_str = _fr('All under')
        portal_path = '/'.join(api.portal.get().getPhysicalPath())
        # search held_positions in personnel-folder
        crit = {'portal_type': 'held_position', 'path': '%s/contacts/personnel-folder' % portal_path,
                'sort_on': ['end', 'sortable_title'], 'sort_order': ['descending', 'ascending']
                }
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        for brain in brains:
            hp.append({'id': brain.UID, 'text': brain.get_full_title})
        # search organizations in plonegroup-organization folder
        crit = {'portal_type': ('organization'), 'sort_on': 'sortable_title',
                'path': '%s/contacts/plonegroup-organization' % portal_path}
        crit.update(query)
        brains = self.context.portal_catalog(**crit)
        make_bis = (len(hp) + len(brains)) > 1 and True or False
        for brain in brains:
            result.append({'id': brain.UID, 'text': brain.get_full_title})
            if make_bis:
                org_bis.append({'id': 'l:%s' % brain.UID, 'text': '%s [%s]' % (brain.get_full_title, all_str)})
        result += hp
        result += org_bis
        return json.dumps(result)


class ServerSentEvents(BrowserView):

    """Send SSE for all file in this context that have just finished its
    documentviewer conversion.

    See https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
    """

    def __call__(self):
        self.request.response.setHeader('Content-Type', 'text/event-stream')
        self.request.response.setHeader('Cache-Control', 'no-cache')
        self.request.response.setHeader('Pragma', 'no-cache')
        response = u''
        for child in self.context.listFolderContents():
            if IFile.providedBy(child):
                if getattr(child, 'conversion_finished', False):
                    info = {
                        u'id': child.getId(),
                        u'path': u'/'.join(child.getPhysicalPath())
                    }
                    if getattr(child, 'just_added', False):
                        child.just_added = False
                        info['justAdded'] = True

                    line = u'data: {}\n\n'.format(json.dumps(info))
                    response = u"{}{}".format(response, line)
                    child.conversion_finished = False

        return response
