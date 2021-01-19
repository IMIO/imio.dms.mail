# -*- coding: utf-8 -*-

from datetime import datetime
from eea.faceted.vocabularies.autocomplete import IAutocompleteSuggest
from imio.dms.mail import _
from imio.dms.mail import _tr
from imio.helpers.emailer import add_attachment
from imio.helpers.emailer import create_html_email
from imio.helpers.emailer import send_email
from imio.helpers.fancytree.views import BaseRenderFancyTree
from plone import api
from plone.app.contenttypes.interfaces import IFile
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from zope.i18n import translate
from zope.interface import implements
from zope.lifecycleevent import modified

import json


class CreateFromTemplateForm(BaseRenderFancyTree):

    """Create a document from a collective.documentgenerator template."""

    root = '/templates/om'

    def label(self):
        return translate(
            _(u"${title}: create from template",
              mapping={'title': safe_unicode(self.context.Title())}),
            context=self.request)

    def get_action_name(self):
        return translate(_("Choose this template"), context=self.request)

    def get_query(self):
        path = self.root_path
        return {
            'path': {'query': path, 'depth': -1},
            'portal_type': (
                'Folder',
                'ConfigurablePODTemplate',
            ),
        }

    def redirect_url(self, uid):
        """Redirect to document generation from selected template."""
        url = self.context.absolute_url()
        params = [
            "template_uid={}".format(uid),
            "output_format=odt",
        ]
        return "{}/persistent-document-generation?{}".format(url, "&".join(params))


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
        all_str = _tr('All under')
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
        all_str = _tr('All under')
        portal_path = '/'.join(api.portal.get().getPhysicalPath())
        # search held_positions in personnel-folder
        crit = {'portal_type': 'held_position', 'path': '%s/contacts/personnel-folder' % portal_path,
                'sort_on': 'sortable_title', 'sort_order': 'ascending'
                # 'sort_on': ['end', 'sortable_title'], 'sort_order': ['descending', 'ascending']  # solr error
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


class UpdateItem(BrowserView):
    """
        update attribute of an item
    """

    def __call__(self):
        if 'assigned_user' in self.request:
            self.context.assigned_user = self.request.get('assigned_user')
            modified(self.context)


class SendEmail(BrowserView):
    """Send an email and update email_status field."""

    def __call__(self):
        # 1 send email
        body = self.context.email_body
        msg = create_html_email(body.output)
        pc = self.context.portal_catalog
        for a_uid in self.context.email_attachments or []:
            res = pc(UID=a_uid)
            if res:
                a_obj = res[0].getObject()
                # if no title, a_obj.file.filename
                add_attachment(msg, a_obj.title, content=a_obj.file.data)
        ret = send_email(msg, self.context.email_subject, self.context.email_sender, self.context.email_recipient,
                         self.context.email_cc)
        if ret:
            api.portal.show_message(_('Your email has been sent.'), self.request)
        else:
            api.portal.show_message(_('Your email has not been sent. Check log for errors.'), self.request,
                                    type='error')
            return

        # 2 Update status on omail
        now = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M')
        status = _tr(u'Email sent at ${date_hour}.', mapping={'date_hour': now})
        if not self.context.email_status:
            self.context.email_status = status
        else:
            self.context.email_status += ' {}'.format(status)
        modified(self.context)
