# -*- coding: utf-8 -*-
from collective.documentgenerator.search_replace.pod_template import SearchAndReplacePODTemplates
from collective.documentgenerator.utils import compute_md5
from imio.dms.mail import PRODUCT_DIR
from imio.dms.mail.migrations.migrate_to_3_1 import Migrate_To_3_1
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING

import mock
import os
import unittest


class TestMigrateTo31(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)

    def test_run(self):
        om = self.portal["templates"]["om"]
        # 3.0 stock intro, with a banned expression, not modified
        intro = om["intro"]
        with SearchAndReplacePODTemplates([intro]) as sr:
            sr.replace("do cell with", "do cell if hasattr(view.real_context, 'classification_folders') with")
        intro.initial_md5 = intro.style_modification_md5 = intro.current_md5
        self.assertFalse(intro.has_been_modified())
        # footer modified by the client, with a banned expression
        footer = om["footer"]
        with SearchAndReplacePODTemplates([footer]) as sr:
            sr.replace("sender=view.get_sender()", "sender=hasattr(view, 'get_sender') and view.get_sender() or {}")
        self.assertTrue(footer.has_been_modified())
        # part b: documentgenerator 16 replaces banned expressions
        self.portal.portal_setup.setLastVersionForProfile("collective.documentgenerator:default", "15")
        with mock.patch.dict(os.environ, {"FUNC_PART": "b"}):
            Migrate_To_3_1(self.portal).run()
        # stock intro reloaded from the 3.1 file
        self.assertFalse(intro.has_been_modified())
        with open(os.path.join(PRODUCT_DIR, "profiles/default/templates/om-intro.odt"), "rb") as fh:
            self.assertEqual(intro.initial_md5, compute_md5(fh.read()))
        with SearchAndReplacePODTemplates([intro, footer]) as sr:
            replaced = sr.search("++REPLACED++")
        self.assertNotIn(intro.UID(), replaced)
        # modified footer kept
        self.assertTrue(footer.has_been_modified())
        self.assertEqual(len(replaced[footer.UID()]), 1)
