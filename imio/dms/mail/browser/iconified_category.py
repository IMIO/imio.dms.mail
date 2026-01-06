# -*- coding: utf-8 -*-
"""
    collective.iconifiedcategory overrided views
"""
from collective.documentgenerator.utils import need_mailing_value
from collective.iconifiedcategory.browser.actionview import ApprovedChangeView as BaseApprovedChangeView
from collective.iconifiedcategory.browser.actionview import SignedChangeView as BaseSignedChangeView
from collective.iconifiedcategory.browser.tabview import ApprovedColumn as BaseApprovedColumn
from collective.iconifiedcategory.browser.tabview import SignedColumn as BaseSignedColumn
from imio.dms.mail.adapters import OMApprovalAdapter
from imio.dms.mail.utils import get_allowed_omf_content_types
from imio.dms.mail.utils import logger  # noqa F401
from plone import api
from plone.memoize.interfaces import ICacheChooser
from zope.component import getUtility
from zope.i18n import translate


"""
{'approval': [[{'approved_by': 'dirg',
                'approved_on': datetime.datetime(2025, 12, 16, 14, 52, 21, 238011),
                'status': 'a'}]],
 'approvers': [['dirg']],
 'current_nb': -1,
 'editors': [True],
 'files': ['57a46bf1f0f842adbdabc6afd05a26ee'],
 'pdf_files': [['355df18ed9404613a1c37651b864aac2']],
 'session_id': 4,
 'signers': [('dirg', u'Maxime DG ()', u'')]
}
"""  # noqa


class ApprovedColumn(BaseApprovedColumn):

    def __init__(self, context, request, table):
        super(ApprovedColumn, self).__init__(context, request, table)
        # self.context is the mail here
        self.approval = OMApprovalAdapter(self.context)
        self.msg = u""

    def alt(self, content):
        return translate(
            self.msg,
            context=self.table.request,
            domain="collective.iconifiedcategory",
        )

    def css_class(self, content):
        av = self.get_action_view(content)
        # is_editable:
        # state: <= "to_approve" OR approval_occurred
        # permission: View
        # category group : approved_activated
        editable = self.is_editable(content) and " editable" or ""
        # when deactivated, anyone see a grey icon
        state = av.p_state
        if self.approval.is_state_before_approve(state=state):  # state < to_approve
            # to-approve class is used when state is prior to to_approve
            if self.is_deactivated(content):  # to_approve is False
                if (not self.approval.approvers or not content.to_sign or not editable or  # noqa W504
                        need_mailing_value(document=content.getObject())):
                    self.msg = u"Deactivated for approval"
                    return " to-approve "
                else:
                    self.msg = u"Deactivated for approval (click to activate)"
                    return " to-approve editable"
            elif editable:  # to_approve is True and editable
                self.msg = u"Activated for approval (click to deactivate)"
                return " active to-approve editable"
            else:
                self.msg = u"Activated for approval"
                return " active to-approve"
        elif self.is_deactivated(content):  # state >= to_approve and to_approve is False
            self.msg = u"Deactivated for approval"
            return " to-approve"
        # when to_approve, the red icon (no class) is shown if :
        #  * no approval at all
        #  * but the current approver see a green icon when he just approved
        elif state == "to_approve":
            approver_number = self.approval.get_approver_nb(av.userid)
            # current user can approve now
            if self.approval.can_approve(av.userid, av.uid):
                if self.approval.is_file_approved(content.UID, nb=approver_number):
                    self.msg = u"Already approved (click to change)"
                    return " active{}".format(editable)
                self.msg = u"Waiting for your approval (click to approve)"
                return editable
            # current user cannot approve now but is an approver
            elif av.userid in self.approval.approvers:
                # approver must yet approve
                current_nb = self.approval.current_nb
                if approver_number is not None and current_nb is not None and approver_number > current_nb:
                    self.msg = u"Waiting for other approval before you can approve"
                    return " waiting"
        # after a first approval, we show a partially or totally approved icon even for a previously approver
        # if content["approved"]:  # all approved  metadata not updated in approve_file function
        if self.approval.is_file_approved(content.UID):  # all approved
            self.msg = u"Totally approved"
            return " totally-approved"
        elif self.approval.is_file_approved(content.UID, totally=False):
            self.msg = u"Partially approved. Still waiting for other approval(s)"
            return " partially-approved"
        else:
            self.msg = u"Waiting for the first approval"
            return " cant-approve"

    def get_url(self, content):
        av = self.get_action_view(content)
        # after to_approve state, no one can click on the icon
        state = av.p_state
        if self.approval.is_state_after_approve(state=state):
            return "#"
        # when to_approve, only an approver can click on the icon
        if state == "to_approve" and not self.approval.can_approve(av.userid, av.uid):
            return "#"
        return "{url}/@@{action}".format(
            url=content.getURL(),
            action=self.get_action_view_name(content),
        )


class ApprovedChangeView(BaseApprovedChangeView):
    permission = "View"

    def __init__(self, context, request):
        super(ApprovedChangeView, self).__init__(context, request)
        self.parent = self.context.__parent__
        self.approval = OMApprovalAdapter(self.parent)
        self.uid = self.context.UID()
        self.msg = u""
        self.reload = False
        self.could_reload = False

    @property
    def p_state(self):
        return api.content.get_state(self.parent)

    @property
    def userid(self):
        return api.user.get_current().getId()

    def _get_next_values(self, old_values):
        """ """
        values = {}
        status = 0
        # logger.info("Before annot change: %s", self.approval.annot)
        # logger.info("Before values change: %s", old_values)
        if self.p_state == "to_approve":
            # in to_approve state, only an approver can approve or not
            values = old_values.copy()
            if old_values["to_approve"] and self.approval.can_approve(self.userid, self.uid):
                # if a second approver tries to also approve after a first one has already, he can't change anything !
                # 1) with one file, the current_nb has changed and can_approve returns False => OK
                # 2) with multiple files, the current_nb is the same, can_approve returns True => problem
                approver_number = self.approval.get_approver_nb(self.userid)
                approved = self.approval.is_file_approved(self.uid, nb=approver_number)
                if approved and self.approval.current_nb is not None:  # already approved at this level
                    status = 0
                    # the message is displayed after the change and must reflect the new status, not the current one !!
                    self.msg = u"Already approved (click to change)"
                    signer_userid = self.approval.signers[self.approval.current_nb]
                    self.approval.unapprove_file(afile=self.context, signer_userid=signer_userid)
                    self.reload = True
                    values["approved"] = False
                else:  # file not approved at this level
                    self.msg = u"Waiting for your approval (click to approve)"
                    # the status is changed (if totally approved) in sub method
                    # must we pass self to update self.msg: no need for now because we reload in all cases !!
                    # FIXME This triggers a transition that further raise Unauthorized in _may_set_values
                    ret, self.reload = self.approval.approve_file(
                        afile=self.context,
                        userid=self.userid,
                        values=values,
                        transition="propose_to_be_signed",
                    )
                    status = int(ret)
                    values["approved"] = ret
                    self.request["approval_occurred"] = True
            elif not values["to_approve"]:  # file must not be approved
                values["approved"] = False
        elif self.approval.is_state_before_approve(state=self.p_state):
            self.could_reload = True
            # before to_approve state, we can only enable or disable to_approve
            if not old_values["to_approve"]:
                values["to_approve"] = True
                values["approved"] = False
                status = 1
                self.approval.add_file_to_approval(self.uid)
                self.msg = u"Activated for approval (click to deactivate)"
            else:
                values["to_approve"] = False
                values["approved"] = False
                status = 0
                self.approval.remove_file_from_approval(self.uid)
                self.msg = u"Deactivated for approval (click to activate)"
        else:
            values = old_values.copy()
            # cannot be in after to_approve state because get_url column method ?
            logger.warn("IN else of approved change view ???")
        # logger.info("After annot change: %s, ", self.approval.annot)
        # logger.info("After values change: %s, %s", status, values)
        return status, values

    def _may_set_values(self, values):
        if self.approval.is_state_after_approve() and not self.request.get("approval_occurred", False):
            return False
        return super(ApprovedChangeView, self)._may_set_values(values)

    def set_values(self, values):
        old_values = self.get_current_values()
        old_approval_status = self.parent.has_approvings()
        status, values = self._get_next_values(old_values)
        super(BaseApprovedChangeView, self).set_values(values)
        if self.could_reload:
            # new_approval_status = self.parent.has_approvings()
            new_approval_status = self.parent.has_approvings()
            if old_approval_status != new_approval_status:
                cache_chooser = getUtility(ICacheChooser)
                the_cache = cache_chooser("imio.dms.mail.browser.actionspanel.DmsOMActionsPanelView__call__")
                the_cache.ramcache.invalidate("imio.dms.mail.browser.actionspanel.DmsOMActionsPanelView__call__")
                self.reload = True
        return status, self.msg

    def __call__(self):
        json_resp = super(ApprovedChangeView, self).__call__()
        if self.reload and json_resp.rstrip().endswith("}"):
            json_resp = json_resp.rstrip()[:-1] + ',"reload": true}'
        return json_resp


class SignedColumn(BaseSignedColumn):

    def __init__(self, context, request, table):
        super(SignedColumn, self).__init__(context, request, table)
        self.approval = OMApprovalAdapter(self.context)
        # self.context is the mail here

    def css_class(self, content):
        av = self.get_action_view(content)
        # is_editable:
        # state not in ("to_approve", "to_print", "sent")
        # permission: View
        # category group : signed_activated
        # allowed file type for signing
        allowed_type = (not getattr(self.context, "esign", False) and True
                        or content.contentType in get_allowed_omf_content_types(esign=True))
        editable = allowed_type and self.is_editable(content) and " editable" or ""
        # when deactivated, anyone will see a grey icon
        # before to_approve
        if av.p_state not in ("to_approve", "to_print", "to_be_signed", "signed", "sent"):
            if self.is_deactivated(content):  # to_sign is False ?
                if not editable or need_mailing_value(document=content.getObject()):
                    return " deactivated "
                else:
                    return " deactivated editable"
            # we don't want to unset to_sign if to_approve is True
            elif editable and (not content.to_sign or not content.to_approve):
                return " editable"
            else:
                return ""
        elif self.is_deactivated(content):  # state >= to_approve and to_sign is False
            return " deactivated"
        else:  # state >= to_approve and to_sign is True
            base_css = self.is_active(content) and ' active' or ''  # signed is True ?
            if av.p_state in ("to_be_signed", "signed"):
                # we don't want to unset to_sign if to_approve is True
                if editable and (not content.to_sign or not content.to_approve):
                    return '{0} editable'.format(base_css)
            return base_css

    def get_url(self, content):
        av = self.get_action_view(content)
        state = av.p_state
        if self.approval.is_state_after_or_approve(state=state) and state != "to_be_signed":
            return "#"
        return '{url}/@@{action}'.format(
            url=content.getURL(),
            action=self.get_action_view_name(content),
        )


class SignedChangeView(BaseSignedChangeView):
    permission = "View"

    def __init__(self, context, request):
        super(SignedChangeView, self).__init__(context, request)
        self.parent = self.context.__parent__
        self.reload = False

    @property
    def p_state(self):
        return api.content.get_state(self.parent)

    def _get_next_values(self, old_values):
        """ """
        values = old_values.copy()
        status = 0
        # logger.info("Before values change: %s", old_values)
        if self.p_state not in ("to_approve", "to_print", "to_be_signed", "signed", "sent"):
            # before to_approve state, we can only enable or disable to_sign
            if old_values['to_sign'] is False:
                values['to_sign'] = True
                values['signed'] = False
                status = 0
            else:
                values['to_sign'] = False
                values['signed'] = False
                status = -1
            self.reload = True
        elif old_values['to_sign'] and self.p_state in ("to_be_signed", "signed"):
            if old_values['signed'] is False:
                values['to_sign'] = True
                values['signed'] = True
                status = 1
            else:
                values['to_sign'] = True
                values['signed'] = False
                status = 0
        # logger.info("After values change: %s, %s", status, values)
        return status, values

    def _may_set_values(self, values):
        if self.p_state in ("to_approve", "to_print", "sent"):
            return False
        return super(SignedChangeView, self)._may_set_values(values)

    def __call__(self):
        json_resp = super(SignedChangeView, self).__call__()
        if self.reload and json_resp.rstrip().endswith("}"):
            json_resp = json_resp.rstrip()[:-1] + ',"reload": true}'
        return json_resp
