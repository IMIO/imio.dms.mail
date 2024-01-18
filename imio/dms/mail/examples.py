# -*- coding: utf-8 -*-
from plone import api
from plone.namedfile.file import NamedBlobImage

import logging
import os


logger = logging.getLogger('imio.dms.mail: setuphandlers')


def add_annexes_types(context):
    """
        Add french test data: ContentCategoryGroup and ContentCategory
    """
    if not context.readDataFile("imiodmsmail_examples_marker.txt"):
        return
    site = context.getSite()
    logger.info('Adding annexes types')
    ccc = site['annexes_types']
    if 'annexes' not in ccc:
        category_group = api.content.create(
            type='ContentCategoryGroup',
            title='Annexes',
            container=ccc,
            id='annexes',
            # confidentiality_activated=True,
            # to_be_printed_activated=True,
            # signed_activated=True,
            # publishable_activated=True,
        )
    icats = (
        ('annex', u'Annexe', u'attach.png'),
        ('deliberation', u'Délibération', u'deliberation_signed.png'),
        ('cahier-charges', u'Cahier des charges', u'cahier.png'),
        ('legal-advice', u'Avis légal', u'legalAdvice.png'),
        ('budget', u'Facture', u'budget.png'),
    )
    for oid, title, img in icats:
        if oid in ccc['annexes']:
            continue
        icon_path = os.path.join(context._profile_path, 'images', img)
        with open(icon_path, 'rb') as fl:
            icon = NamedBlobImage(fl.read(), filename=img)
        api.content.create(
            type='ContentCategory',
            title=title,
            container=category_group,
            icon=icon,
            id=oid,
            predefined_title=title,
            # confidential=True,
            # to_print=True,
            # to_sign=True,
            # signed=True,
            # publishable=True,
            # only_pdf=True,
            # show_preview=1,
        )
