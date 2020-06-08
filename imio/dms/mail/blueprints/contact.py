# -*- coding: utf-8 -*-

from collective.contact.importexport.blueprints.main import ANNOTATION_KEY
from collective.contact.plonegroup.config import PLONEGROUP_ORG
from collective.transmogrifier.interfaces import ISection
from collective.transmogrifier.interfaces import ISectionBlueprint
from zope.annotation.interfaces import IAnnotations
from zope.interface import classProvides
from zope.interface import implements

import os


class PlonegroupOrganizationPath(object):
    classProvides(ISectionBlueprint)
    implements(ISection)

    def __init__(self, transmogrifier, name, options, previous):
        self.pgo_title = options.get('title', '').strip().decode('utf8')
        self.previous = previous
        self.storage = IAnnotations(transmogrifier).get(ANNOTATION_KEY)
        self.directory_path = self.storage['directory_path']

    def __iter__(self):
        for item in self.previous:
            if self.pgo_title and item['_type'] == 'organization' and self.pgo_title == item['title']:
                item['_path'] = os.path.join(self.directory_path, PLONEGROUP_ORG)
                item['use_parent_address'] = False
            yield item
