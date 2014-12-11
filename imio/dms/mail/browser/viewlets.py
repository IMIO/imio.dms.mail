# -*- coding: utf-8 -*-
from zope.component import getUtility
from zope.intid.interfaces import IIntIds
from zc.relation.interfaces import ICatalog
from plone.app.layout.viewlets import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.contact.widget.interfaces import IContactContent


class ContactContentBackrefsViewlet(ViewletBase):
    #def update(self):
    #    super(ContactContentBackrefsViewlet, self).update()

    def backrefs(self):
        # indirection method added to be easier overrided
        return sorted(self.find_relations(), key=lambda obj: obj.created(), reverse=True)

    def find_relations(self, from_attribute=None, from_interfaces_flattened=None):
        """
            Parameters:
            - from_attribute: schema attribute string
            - from_interfaces_flattened: Interface class (only one)
        """
        ret = []
        catalog = getUtility(ICatalog)
        intids = getUtility(IIntIds)
        query = {'to_id': intids.getId(self.context)}
        if from_attribute is not None:
            query['from_attribute'] = from_attribute
        if from_interfaces_flattened is not None:
            query['from_interfaces_flattened'] = from_interfaces_flattened
        for relation in catalog.findRelations(query):
            # we skip relations between contacts (already shown)
            # nevertheless what about heldposition references for a person: subquery ?
            if IContactContent.providedBy(relation.from_object):
                continue
            # PERFORMANCE TEST TO DO: use directly objects or use the path as request in the portal_catalog to find brain
            ret.append(relation.from_object)
        return ret

    index = ViewPageTemplateFile("contactcontent_backrefs.pt")
