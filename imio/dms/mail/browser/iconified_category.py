# -*- coding: utf-8 -*-
"""
    collective.iconifiedcategory overrided views
"""
from collective.iconifiedcategory.browser.actionview import ApprovedChangeView as BaseApprovedChangeView
from collective.iconifiedcategory.browser.tabview import ApprovedColumn as BaseApprovedColumn
from imio.dms.mail.utils import add_file_to_approval
from imio.dms.mail.utils import approve_file
from imio.dms.mail.utils import can_approve
from imio.dms.mail.utils import get_approval_annot
from imio.dms.mail.utils import is_file_approved
from imio.dms.mail.utils import logger  # noqa F401
from imio.dms.mail.utils import remove_file_from_approval
from plone import api
from zope.i18n import translate


# TODO esign
# ajouter des couleurs différentes pour quelqu'un qui ne peut pas approuver ou pas encore...


"""
{
    'approval': 1,
    'files': {'4115fb4c265647ca82d85285504973b8': {1: {'status': 'p'}, 2: {'status': 'w'}}},
    'numbers': {
        1: {'status': 'p', 'signer': ('dirg', 'stephan.geulette@imio.be', u'Maxime DG', u'Directeur G\xe9n\xe9ral'),
            'users': ['dirg']},
        2: {'status': 'w', 'signer': ('bourgmestre', 'stephan.geulette+s2@imio.be', u'Paul BM', u'Bourgmestre'),
            'users': ['bourgmestre', 'chef']}},
    'session_id': None,
    'users': {'bourgmestre': {'status': 'w', 'editor': False, 'name': u'Monsieur Paul BM', 'order': 2},
              'chef': {'status': 'w', 'editor': False, 'name': u'Monsieur Michel Chef', 'order': 2},
              'dirg': {'status': 'w', 'editor': True, 'name': u'Monsieur Maxime DG', 'order': 1}},
}
"""  # noqa


class ApprovedColumn(BaseApprovedColumn):

    the_object = True

    def __init__(self, context, request, table):
        super(ApprovedColumn, self).__init__(context, request, table)
        # self.context is the mail here
        self.a_a = get_approval_annot(self.context)
        self.msg = u""
        self.base_class = "iconified-action"

    def alt(self, content):
        return translate(
            self.msg,
            context=self.table.request,
            domain='collective.iconifiedcategory',
        )

    def css_class(self, content):
        av = self.get_action_view(content)
        editable = self.is_editable(content) and " editable" or ""
        # when deactivated, anyone see a grey icon
        if av.p_state not in ("to_approve", "to_print", "to_be_signed", "signed", "sent"):
            # to-approve class is used when state is prior to to_approve
            if self.is_deactivated(content):
                if not self.a_a["users"] or not editable:
                    self.msg = u"Deactivated for approval"
                    return " to-approve "
                else:
                    self.msg = u"Deactivated for approval (click to activate)"
                    return " to-approve editable"
            elif editable:
                self.msg = u"Activated for approval (click to deactivate)"
                return " active to-approve editable"
            else:
                self.msg = u"Activated for approval"
                return " active to-approve"
        elif self.is_deactivated(content):
            self.base_class = "iconified-action-approved"
            self.msg = u"Deactivated for approval"
            return " to-approve"
        # when to_approve, the red icon (no class) is shown if :
        #  * no approval at all
        #  * but the current approver see a green icon when he just approved
        elif av.p_state == "to_approve":
            self.base_class = "iconified-action-approved"
            # current user can approve now
            if can_approve(self.a_a, av.userid, av.uid):
                if self.a_a["files"][content.UID][self.a_a["approval"]]["status"] == "a":
                    self.msg = u"Already approved (click to change)"
                    return " active{}".format(editable)
                self.msg = u"Waiting for your approval (click to approve)"
                return editable
            # current user cannot approve now but is an approver
            elif av.userid in self.a_a["users"]:
                # approver must yet approve
                if self.a_a["users"][av.userid]["order"] > self.a_a["approval"]:
                    self.msg = u"Waiting for other approval before you can approve"
                    return " waiting"
        # after a first approval, we show a partially or totally approved icon even for a previously approver
        if content["approved"]:  # all approved
            self.msg = u"Totally approved"
            return " totally-approved"
        elif is_file_approved(self.a_a, content.UID, totally=False):
            self.msg = u"Partially approved. Still waiting for other approval(s)"
            return " partially-approved"
        else:
            self.msg = u"Waiting for the first approval"
            return " cant-approve"
        return ""

    def get_url(self, content):
        av = self.get_action_view(content)
        # after to_approve state, no one can click on the icon
        if av.p_state in ("to_print", "to_be_signed", "signed", "sent"):
            return "#"
        # when to_approve, only an approver can click on the icon
        if av.p_state == "to_approve" and not can_approve(self.a_a, av.userid, av.uid):
            return "#"
        return '{url}/@@{action}'.format(
            url=content.getURL(),
            action=self.get_action_view_name(content),
        )

    def renderCell(self, content):
        link = (u'<a href="{0}" class="{3}{1}" alt="{2}" '
                u'title="{2}"></a>')
        return link.format(
            self.get_url(content),
            self.css_class(content),
            self.alt(content),
            self.base_class,
        )


class ApprovedChangeView(BaseApprovedChangeView):
    permission = "View"

    def __init__(self, context, request):
        super(ApprovedChangeView, self).__init__(context, request)
        self.parent = self.context.__parent__
        self.p_state = api.content.get_state(self.parent)
        self.a_a = get_approval_annot(self.parent)
        self.reload = False
        self.user_id = None
        self.uid = self.context.UID()
        self.msg = u""

    @property
    def userid(self):
        if self.user_id is None:
            self.user_id = api.user.get_current().getId()
        return self.user_id

    def _get_next_values(self, old_values):
        """ """
        values = {}
        status = 0
        # logger.info("Before annot change: %s", self.a_a)
        # logger.info("Before values change: %s", old_values)
        if self.p_state == "to_approve":
            # in to_approve state, only an approver can approve or not
            if can_approve(self.a_a, self.userid, self.uid):
                if self.a_a["files"][self.uid][self.a_a["approval"]]["status"] == "a":
                    status = 0
                    self.msg = u"Already approved (click to change)"
                    # TODO TO BE HANDLED
                else:
                    self.msg = u"Waiting for your approval (click to approve)"
                    # the status is changed (if totally approved) in sub method
                    # must we pass self to update self.msg: no need for now because we reload in all cases !!
                    ret, self.reload = approve_file(self.a_a, self.parent, self.context, self.userid, values=values,
                                                    transition="propose_to_be_signed")
                    status = int(ret)
        elif self.p_state not in ("to_print", "to_be_signed", "signed", "sent"):
            # before to_approve state, we can only enable or disable to_approve
            if old_values['to_approve'] is False:
                values['to_approve'] = True
                values['approved'] = False
                status = 1
                add_file_to_approval(self.a_a, self.uid)
                self.msg = u"Activated for approval (click to deactivate)"
            else:
                values['to_approve'] = False
                values['approved'] = False
                status = 0
                remove_file_from_approval(self.a_a, self.uid)
                self.msg = u"Deactivated for approval (click to activate)"
            self.reload = False
        else:
            # cannot be in after to_approve state because get_url column method ?
            logger.warn("IN else of approved change view ???")
        # logger.info("After annot change: %s, ", self.a_a)
        # logger.info("After values change: %s, %s", status, values)
        return status, values

    def _may_set_values(self, values):
        if self.p_state in ("to_print", "to_be_signed", "signed", "sent"):
            return False
        return super(ApprovedChangeView, self)._may_set_values(values)

    def set_values(self, values):
        old_values = self.get_current_values()
        status, values = self._get_next_values(old_values)
        super(BaseApprovedChangeView, self).set_values(values)
        return status, self.msg

    def __call__(self):
        # TODO ajouter un comparatif de date afin de voir si on agit bien sur qlq chose à jour...
        json_resp = super(ApprovedChangeView, self).__call__()
        if self.reload and json_resp.rstrip().endswith("}"):
            # logger.info("RELOAD TRUE")
            json_resp = json_resp.rstrip()[:-1] + ',"reload": true}'
        return json_resp
