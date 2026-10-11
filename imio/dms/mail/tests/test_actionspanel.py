# -*- coding: utf-8 -*-
"""Test actions panels."""
from collective.documentgenerator.browser.actionspanel import ConfigurablePODTemplateActionsPanelView
from collective.iconifiedcategory.utils import calculate_category_id
from imio.dms.mail.browser.actionspanel import actionspanelview_cachekey
from imio.dms.mail.browser.actionspanel import ActionsPanelViewletAllButTransitions
from imio.dms.mail.browser.actionspanel import AnnexActionsPanelView
from imio.dms.mail.browser.actionspanel import BasicActionsPanelView
from imio.dms.mail.browser.actionspanel import CategoryActionsPanelView
from imio.dms.mail.browser.actionspanel import ClassificationActionsPanelView
from imio.dms.mail.browser.actionspanel import ClassificationContainersActionsPanelView
from imio.dms.mail.browser.actionspanel import ClassificationFolderActionsPanelView
from imio.dms.mail.browser.actionspanel import CPODTActionsPanelView
from imio.dms.mail.browser.actionspanel import DmsFileActionsPanelView
from imio.dms.mail.browser.actionspanel import DmsSignRequestActionsPanelView
from imio.dms.mail.browser.actionspanel import DmsTaskActionsPanelView
from imio.dms.mail.browser.actionspanel import MultipleAnnexesMixin
from imio.dms.mail.browser.actionspanel import OnlyAddActionsPanelView
from imio.dms.mail.browser.actionspanel import SigningFieldsetActionsPanelView
from imio.dms.mail.Extensions.demo import activate_signing
from imio.dms.mail.interfaces import IImioDmsMailLayer
from imio.dms.mail.testing import change_user
from imio.dms.mail.testing import create_sign_request
from imio.dms.mail.testing import DMSMAIL_INTEGRATION_TESTING
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import get_object
from plone import api
from plone.dexterity.utils import createContentInContainer
from plone.namedfile.file import NamedBlobFile
from z3c.relationfield.relation import RelationValue
from zope.component import createObject
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.intid.interfaces import IIntIds
from zope.lifecycleevent import modified

import unittest


class TestActionspanel(unittest.TestCase):
    """Module functions."""

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_actionspanelview_cachekey(self):
        portal = self.layer["portal"]
        user = api.user.get(username="siteadmin")
        portal.REQUEST["AUTHENTICATED_USER"] = user
        im2 = get_object(oid="courrier2", ptype="dmsincomingmail")
        view = im2.unrestrictedTraverse("@@actions_panel")
        self.assertEqual(
            actionspanelview_cachekey(None, view),
            (True, False, False, False, True, "/".join(im2.getPhysicalPath()), "siteadmin",
             im2.modified().strftime("%Y%m%d-%H%M%S-%f"), get_plone_groups_for_user(user=user)),
        )
        self.assertEqual(
            actionspanelview_cachekey(None, view, useIcons=False, showActions=True)[0:3], (False, False, True)
        )


class TestMultipleAnnexesMixin(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_render_multiple_annexes_button(self):
        self.assertRaises(NotImplementedError, MultipleAnnexesMixin().render_multiple_annexes_button)


class TestDmsIMActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username="siteadmin")
        self.im2 = get_object(oid="courrier2", ptype="dmsincomingmail")
        self.view = self.im2.unrestrictedTraverse("@@actions_panel")
        self.intids = getUtility(IIntIds)

    def test_mayReply(self):
        self.assertEqual(api.content.get_state(self.im2), "created")
        self.assertTrue(self.view.mayReply())
        # change state
        api.content.transition(self.im2, "propose_to_manager")
        self.assertEqual(api.content.get_state(self.im2), "proposed_to_manager")
        self.assertTrue(self.view.mayReply())
        # change title
        self.im2.title = None
        self.assertFalse(self.view.mayReply())
        self.im2.title = u"title"
        # removed permission
        api.content.transition(self.im2, to_state="proposed_to_agent")
        change_user(self.portal, "lecteur")
        self.view.request.set("imio.actionspanel_member_cachekey", None)
        self.assertFalse(self.view.mayReply())

    def test_renderReplyButton(self):
        api.content.transition(self.im2, "propose_to_manager")
        self.view.useIcons = True
        self.assertEqual(
            self.view.renderReplyButton(),
            '<td class="noPadding">\n  <a target="_parent" href="{}'
            '/@@reply">\n     \n     <img title="Reply" src=" http://nohost/plone/'
            '++resource++imio.dms.mail/reply_icon.png" />\n  </a>\n</td>'
            "\n".format(self.im2.absolute_url()),
        )
        #                         '<td class="noPadding"></td>\n'.format(self.im2.absolute_url()))
        self.view.useIcons = False
        self.assertEqual(
            self.view.renderReplyButton(),
            '<td class="noPadding">\n  <a target="_parent" href="{}'
            '/@@reply">\n     <input type="button" value="Reply" class="apButton apButtonAction '
            'apButtonAction_reply" />\n     \n  </a>\n</td>'
            "\n".format(self.im2.absolute_url()),
        )

    #                         '<td class="noPadding"></td>\n'.format(self.im2.absolute_url()))

    def test_renderAssignUser(self):
        self.view.useIcons = False
        self.assertEqual(api.content.get_state(self.view.context), "created")
        self.assertEqual(self.view.renderAssignUser(), "")
        api.content.transition(self.view.context, "propose_to_manager")
        # right state
        self.assertEqual(
            self.view.renderAssignUser(),
            u'<td>\n    <form action="">\n      <select name="Assign" onchange="javascript:'
            u"callViewAndReload(base_url='{}', view_name='@@update_item', params={{'assigned_user': "
            u'this.value}})" class="apButton apButtonSelect apButtonAction apButtonAction_assign">\n'
            u'        <option style="display:none" value="#">Assign</option>\n        \n        '
            u'<option value="agent">Fred Agent</option>\n        <option value="encodeur">Jean Encodeur'
            u"</option>\n      </select>\n    </form>\n</td>"
            u"\n".format(self.im2.absolute_url()),
        )
        self.view.useIcons = True
        self.assertEqual(
            self.view.renderAssignUser(),
            u'<td>\n    <form action="">\n      <select name="Assign" onchange="javascript:'
            u"callViewAndReload(base_url='{}', view_name='@@update_item', params={{'assigned_user': "
            u'this.value}})" class="apButton apButtonSelect apButtonAction apButtonAction_assign '
            u'apUseIcons">\n        \n        <option style="display:none" value="#"></option>\n        '
            u'<option value="agent">Fred Agent</option>\n        <option value="encodeur">Jean Encodeur'
            u"</option>\n      </select>\n    </form>\n</td>"
            u"\n".format(self.im2.absolute_url()),
        )
        # without treating_groups
        new = api.content.create(self.portal["incoming-mail"], "dmsincomingmail", "c1")
        view = new.unrestrictedTraverse("@@actions_panel")
        view.useIcons = True
        self.assertEqual(view.renderAssignUser(), "")

    def test_sortTransitions(self):
        self.assertListEqual([t["id"] for t in self.view.getTransitions()], ["propose_to_manager", "propose_to_agent"])
        api.content.transition(obj=self.im2, to_state="proposed_to_agent")
        # with caching
        self.assertListEqual([t["id"] for t in self.view.getTransitions()], ["propose_to_manager", "propose_to_agent"])
        # without caching
        self.assertListEqual(
            [t["id"] for t in self.view.getTransitions(caching=False)],
            ["back_to_creation", "back_to_manager", "treat", "close"],
        )
        to_sort = [{"id": "close"}, {"id": "back_to_creation"}, {"id": "treat"}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(to_sort, [{"id": "back_to_creation"}, {"id": "treat"}, {"id": "close"}])
        to_sort = [{"id": "unknown"}, {"id": "close"}, {"id": "back_to_creation"}, {"id": "treat"}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(to_sort, [{"id": "back_to_creation"}, {"id": "treat"}, {"id": "close"}, {"id": "unknown"}])

    def test_multiple_annexes(self):
        self.assertTrue(self.view.may_multiple_annexes())
        self.view.useIcons = False
        result = self.view.render_multiple_annexes_button()
        self.assertIn("quick_upload?typeupload=dmsappendixfile", result)
        self.assertIn("Multiple annexes", result)

        # not shown when in faceted navigation
        self.view.request["URL"] = "http://nohost/plone/@@faceted_query"
        self.assertFalse(self.view.may_multiple_annexes())

    def test_im_actionspanel_cache(self):
        # TODO update this irrelevant test
        ret0 = self.view()
        # we have 5 actions: edit, propose manager, propose agent, reply, multiple_annexes
        self.assertEqual(ret0.count(u"<td "), 6)
        api.content.transition(self.im2, "propose_to_agent")
        ret1 = self.view()
        # we have the same transitions because there is a cache on getTransitions
        # we have also assign but it starts with <td>
        self.assertEqual(ret1.count(u"<td "), 6)
        # we add a reply
        om2 = get_object(oid="reponse2", ptype="dmsoutgoingmail")
        om2.reply_to = [RelationValue(self.intids.getId(self.im2))]
        modified(om2)
        ret2 = self.view()
        self.assertEqual(ret2.count(u"<td "), 6)


class TestDmsOMActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username="siteadmin")
        self.om = get_object(oid="reponse2", ptype="dmsoutgoingmail")
        self.view = self.om.unrestrictedTraverse("@@actions_panel")
        self.view.useIcons = False

    def test_sortTransitions(self):
        to_sort = [{"id": "mark_as_sent"}, {"id": "propose_to_n_plus_1"}, {"id": "back_to_creation"}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(
            to_sort, [{"id": "back_to_creation"}, {"id": "propose_to_n_plus_1"}, {"id": "mark_as_sent"}]
        )

    def test_may_create_from_template(self):
        self.assertTrue(self.view.may_create_from_template())
        change_user(self.portal, "lecteur")
        self.view.request.set("imio.actionspanel_member_cachekey", None)
        self.assertFalse(self.view.may_create_from_template())

    def test_render_create_from_template_button(self):
        rendered = self.view.render_create_from_template_button()
        self.assertIn(u'href="{}/@@create-from-template"'.format(self.om.absolute_url()), rendered)
        # Plone 4 overlay
        self.assertIn(u'class="overlay overlay-ajax overlay-template-selection"', rendered)
        self.assertIn(u'value="Create from template"', rendered)
        self.view.request["URL"] = "http://nohost/plone/@@faceted_query"
        self.assertEqual(self.view.render_create_from_template_button(), "")

    def test_may_create_new_message(self):
        self.assertFalse(self.view.may_create_new_message())
        self.om.send_modes = [u"email"]
        self.assertTrue(self.view.may_create_new_message())

    def test_render_create_new_message(self):
        self.assertEqual(self.view.render_create_new_message(), "")
        self.om.send_modes = [u"email"]
        rendered = self.view.render_create_new_message()
        self.assertIn(u'href="{}/edit?edit-email=1#fieldsetlegend-email"'.format(self.om.absolute_url()), rendered)
        self.assertIn(u'class="apButton apButtonAction apButtonAction_wemail"', rendered)
        self.om.email_subject = u"Subject"
        self.assertIn(u'class="apButton apButtonAction apButtonAction_wemail_ok"',
                      self.view.render_create_new_message())

    def test_may_send_email(self):
        self.om.send_modes = [u"email"]
        self.assertFalse(self.view.may_send_email())
        self.om.email_subject = u"Subject"
        self.assertTrue(self.view.may_send_email())

    def test_render_send_email(self):
        self.assertEqual(self.view.render_send_email(), "")
        self.om.send_modes = [u"email"]
        self.om.email_subject = u"Subject"
        rendered = self.view.render_send_email()
        # Plone 4: the email is sent by a GET ajax call
        self.assertIn(
            u"onclick=\"javascript:callViewAndReload(base_url='{}', view_name='@@send_email')\"".format(
                self.om.absolute_url()),
            rendered,
        )
        self.assertIn(u'class="apButton apButtonAction apButtonAction_sendemail"', rendered)

    def test_call(self):
        rendered = self.view(useIcons=False)
        self.assertIn(u"@@create-from-template", rendered)
        self.assertIn(u"quick_upload?typeupload=dmsappendixfile", rendered)
        self.assertIn(u"apButtonWF_propose_to_be_signed", rendered)
        self.assertNotIn(u"@@send_email", rendered)

    def test_multiple_annexes(self):
        self.assertTrue(self.view.may_multiple_annexes())
        self.view.useIcons = False
        result = self.view.render_multiple_annexes_button()
        self.assertIn("quick_upload?typeupload=dmsappendixfile", result)
        self.assertIn("Multiple annexes", result)

        # not shown when in faceted navigation
        self.view.request["URL"] = "http://nohost/plone/@@faceted_query"
        self.assertFalse(self.view.may_multiple_annexes())


class TestSigningFieldsetActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username="siteadmin")
        activate_signing(self.portal)
        self.om = get_object(oid="reponse1", ptype="dmsoutgoingmail")
        self.view = self.om.unrestrictedTraverse("@@signing_actions_panel")

    def test_fieldset(self):
        self.assertIsInstance(self.view, SigningFieldsetActionsPanelView)
        self.assertEqual(self.view.fieldset, "#fieldsetlegend-signing")

    def test_renderEdit(self):
        self.view.showEdit = True
        self.view.kwargs = {}
        self.view.useIcons = True
        rendered = self.view.renderEdit()
        self.assertIn(u'href="{}/edit#fieldsetlegend-signing"'.format(self.om.absolute_url()), rendered)
        self.assertIn(u'src="http://nohost/plone/edit.png"', rendered)
        self.view.useIcons = False
        rendered = self.view.renderEdit()
        self.assertIn(u'action="{}/edit#fieldsetlegend-signing"'.format(self.om.absolute_url()), rendered)
        self.view.showEdit = False
        self.assertEqual(self.view.renderEdit(), "")

    def test_call(self):
        rendered = self.view()
        self.assertIn(u"edit#fieldsetlegend-signing", rendered)
        # no transition
        self.assertNotIn(u"apButtonWF", rendered)


class TestDmsSignRequestActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username="siteadmin")
        self.sreq, self.files = create_sign_request(self.portal, oid="sr-panel", nb_files=1)
        self.view = self.sreq.unrestrictedTraverse("@@actions_panel")

    def test_sortTransitions(self):
        self.assertIsInstance(self.view, DmsSignRequestActionsPanelView)
        to_sort = [{"id": "unknown"}, {"id": "close"}, {"id": "propose_to_approve"}, {"id": "back_to_creation"}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(
            to_sort, [{"id": "back_to_creation"}, {"id": "propose_to_approve"}, {"id": "close"}, {"id": "unknown"}]
        )

    def test_call(self):
        rendered = self.view(useIcons=False)
        self.assertIn(u"apButtonWF_propose_to_approve", rendered)
        self.assertIn(u"quick_upload?typeupload=dmsappendixfile", rendered)


class TestDmsFileActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_listObjectButtonsActions(self):
        portal = self.layer["portal"]
        change_user(portal)
        omf = get_object(oid="reponse1", ptype="dmsoutgoingmail")["1"]
        view = omf.unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, DmsFileActionsPanelView)
        self.assertListEqual(
            [act["id"] for act in view.listObjectButtonsActions()],
            ["external_edit", "rename_title", "download", "view_element", "delete"],
        )


class TestDmsTaskActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username="siteadmin")
        self.task = get_object(oid="courrier1", ptype="dmsincomingmail")["tache1"]
        self.view = self.task.unrestrictedTraverse("@@actions_panel")

    def test_sortTransitions(self):
        self.assertIsInstance(self.view, DmsTaskActionsPanelView)
        to_sort = [{"id": "do_closed"}, {"id": "do_to_assign"}, {"id": "back_in_created"}]
        self.view.sortTransitions(to_sort)
        self.assertListEqual(to_sort, [{"id": "back_in_created"}, {"id": "do_to_assign"}, {"id": "do_closed"}])

    def test_call(self):
        rendered = self.view(useIcons=False)
        self.assertIn(u"apButtonWF_do_to_assign", rendered)
        self.assertListEqual(self.view.ACCEPTABLE_ACTIONS, ["copy", "cut", "paste", "delete"])


class TestClassificationFolderActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_call(self):
        portal = self.layer["portal"]
        change_user(portal)
        portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username="siteadmin")
        folder = portal["folders"]["ordre-public-reglement-general-de-police"]
        view = folder.unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, ClassificationFolderActionsPanelView)
        rendered = view(useIcons=False)
        self.assertIn(u"quick_upload?typeupload=annex", rendered)
        self.assertListEqual(view.ACCEPTABLE_ACTIONS, ["cut", "copy", "paste", "delete"])


class TestClassificationContainersActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        portal = self.layer["portal"]
        change_user(portal)
        for container in (portal["tree"], portal["folders"]):
            view = container.unrestrictedTraverse("@@actions_panel")
            self.assertIsInstance(view, ClassificationContainersActionsPanelView)
            rendered = view(useIcons=False)
            self.assertIn(u'action="{}/@@import"'.format(container.absolute_url()), rendered)
            self.assertIn(u'action="{}/@@refresh-cache"'.format(container.absolute_url()), rendered)
        self.assertIn(u'action="http://nohost/plone/tree/add-ClassificationCategory"',
                      portal["tree"].unrestrictedTraverse("@@actions_panel")(useIcons=False))


class TestClassificationActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        portal = self.layer["portal"]
        change_user(portal)
        # a category is not a content type: the tree container stores it (as its add form does)
        category = createObject("ClassificationCategory")
        category.identifier = u"001"
        category.title = u"Catégorie"
        portal["tree"]._add_element(category)
        category = portal["tree"].get_by("identifier", u"001")
        view = category.unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, ClassificationActionsPanelView)
        self.assertListEqual(view.ACCEPTABLE_ACTIONS,
                             ["cut", "copy", "paste", "delete", "rename", "classification.tree.add"])
        self.assertIn(u"add-ClassificationCategory", view(useIcons=False))


class TestOnlyAddActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        portal = self.layer["portal"]
        change_user(portal)
        view = portal["annexes_types"]["annexes"].unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, OnlyAddActionsPanelView)
        self.assertListEqual(view.ACCEPTABLE_ACTIONS, ["paste"])
        self.assertNotIn(u"delete", view(useIcons=False, showOwnDelete=False))


class TestAnnexActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        change_user(self.portal)
        self.portal.REQUEST["AUTHENTICATED_USER"] = api.user.get(username="siteadmin")
        folder = self.portal["folders"]["ordre-public-reglement-general-de-police"]
        self.annex = createContentInContainer(
            folder, "annex", title=u"Annexe", file=NamedBlobFile(b"content", filename=u"annexe.txt"),
            content_category=calculate_category_id(self.portal["annexes_types"]["annexes"]["annex"]),
        )

    def test_init(self):
        view = self.annex.unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, AnnexActionsPanelView)
        self.assertEqual(view.IGNORABLE_ACTIONS, ("documentviewer_convert", "view_preview", "view_element"))
        self.portal.REQUEST["URL"] = "http://nohost/plone/folders/@@faceted_query"
        view = self.annex.unrestrictedTraverse("@@actions_panel")
        self.assertEqual(view.IGNORABLE_ACTIONS, ("documentviewer_convert", "view_preview"))

    def test_call(self):
        rendered = self.annex.unrestrictedTraverse("@@actions_panel")(useIcons=False)
        self.assertIn(u"{}/edit".format(self.annex.absolute_url()), rendered)
        self.assertNotIn(u"apButtonWF", rendered)
        self.assertNotIn(u"view_element", rendered)


class TestCPODTActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        portal = self.layer["portal"]
        change_user(portal)
        alsoProvides(portal.REQUEST, IImioDmsMailLayer)
        view = portal["templates"]["om"]["main"].unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, CPODTActionsPanelView)
        self.assertIsInstance(view, ConfigurablePODTemplateActionsPanelView)
        self.assertListEqual(view.ACCEPTABLE_ACTIONS, ["cut", "copy", "paste", "delete", "rename"])
        rendered = view()
        self.assertIn(u"http://nohost/plone/templates/om/main/object_copy", rendered)
        self.assertIn(u"http://nohost/plone/templates/om/main/edit", rendered)


class TestBasicActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        portal = self.layer["portal"]
        change_user(portal)
        view = portal["contacts"]["swde"].unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, BasicActionsPanelView)
        self.assertListEqual(view.ACCEPTABLE_ACTIONS, ["cut", "copy", "paste", "delete", "rename"])
        self.assertIn(u"http://nohost/plone/contacts/swde/edit", view())


class TestCategoryActionsPanelView(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_init(self):
        portal = self.layer["portal"]
        change_user(portal)
        view = portal["annexes_types"]["annexes"]["annex"].unrestrictedTraverse("@@actions_panel")
        self.assertIsInstance(view, CategoryActionsPanelView)
        self.assertListEqual(view.ACCEPTABLE_ACTIONS, ["copy", "delete", "rename", "update_categorized_elements"])


class TestActionsPanelViewletAllButTransitions(unittest.TestCase):

    layer = DMSMAIL_INTEGRATION_TESTING

    def test_show(self):
        portal = self.layer["portal"]
        change_user(portal)
        # hidden period folder
        im1 = get_object(oid="courrier1", ptype="dmsincomingmail")
        period = im1.__parent__
        period.REQUEST["ACTUAL_URL"] = period.absolute_url()
        viewlet = ActionsPanelViewletAllButTransitions(period, period.REQUEST, None, None)
        self.assertFalse(viewlet.show())
        tplf = portal["templates"]["om"]
        tplf.REQUEST["ACTUAL_URL"] = tplf.absolute_url()
        viewlet = ActionsPanelViewletAllButTransitions(tplf, tplf.REQUEST, None, None)
        self.assertTrue(viewlet.show())
