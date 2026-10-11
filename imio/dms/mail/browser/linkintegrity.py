# -*- coding: utf-8 -*-
"""Link integrity breaches computed at delete confirmation (Plone 6 has no breach storage)."""
from collective.contact.plonegroup.browser.linkintegrity import PlonegroupDeleteConfirmationInfo
from collective.contact.plonegroup.interfaces import IPloneGroupContact
from collective.contact.plonegroup.subscribers import search_value_in_objects
from imio.dms.mail.interfaces import IPersonnelContact
from imio.dms.mail.utils import is_hp_used_in_signer_rules
from imio.helpers.content import uuidToObject
from imio.helpers.security import check_zope_admin
from plone import api
from plone.app.linkintegrity.browser.info import DeleteConfirmationInfo
from plone.uuid.interfaces import IUUID

import copy


PLONEGROUP_FIELDS = {
    "dmsincomingmail": ["treating_groups", "recipient_groups"],
    "dmsincoming_email": ["treating_groups", "recipient_groups"],
    "dmsoutgoingmail": ["treating_groups", "recipient_groups"],
    "task": ["assigned_group", "enquirer", "parents_assigned_groups", "parents_enquirers"],
}


def esign_breach_sources(obj):
    """Return the objects that keep an om/sign_request file in the approval (esign) process."""
    if obj.portal_type not in ("dmsommainfile", "dmsappendixfile") or obj.__parent__.portal_type not in (
        "dmsoutgoingmail",
        "sign_request",
    ):
        return []
    approval = obj.__parent__.approval()
    if approval.is_state_after_or_approve() and not check_zope_admin():
        return []  # the deletion is refused with a message by subscribers.i_annex_will_be_removed
    uid = obj.UID()
    if uid in [f_uid for lst in approval.pdf_files_uids for f_uid in lst]:
        c_f_uid = getattr(obj, "conv_from_uid", None)
        c_obj = c_f_uid and uuidToObject(c_f_uid, unrestricted=True) or None
        return [c_obj or obj.__parent__]
    if uid in approval.files_uids:
        return [obj.__parent__]
    return []


def personnel_breach_sources(obj):
    """Return the outgoing mails using a personnel held position as sender, or the outgoing-mail folder when it is
    used in the signer rules."""
    if obj.portal_type != "held_position" or not IPersonnelContact.providedBy(obj):
        return []
    catalog = api.portal.get_tool("portal_catalog")
    sources = [
        brain._unrestrictedGetObject()
        for brain in catalog.unrestrictedSearchResults(portal_type=["dmsoutgoingmail"], sender_index=[obj.UID()])
    ]
    if is_hp_used_in_signer_rules(obj, []):
        sources.append(api.portal.get()["outgoing-mail"])
    return sources


class DmsDeleteConfirmationInfo(PlonegroupDeleteConfirmationInfo):
    """Plonegroup breaches restricted to the dms fields, plus esign files and personnel held positions."""

    def check_object(self, obj, excluded_path=None, excluded_paths=None):
        breaches = DeleteConfirmationInfo.check_object(
            self, obj, excluded_path=excluded_path, excluded_paths=excluded_paths
        )
        sources = esign_breach_sources(obj) + personnel_breach_sources(obj)
        if IPloneGroupContact.providedBy(obj):
            sources += (
                search_value_in_objects(
                    obj, obj.UID(), p_types=list(PLONEGROUP_FIELDS), type_fields=copy.deepcopy(PLONEGROUP_FIELDS)
                )
                or []
            )
        if not sources:
            return breaches
        if not breaches:
            breaches = {
                "sources": [],
                "target": {
                    "uid": IUUID(obj),
                    "title": obj.Title(),
                    "url": obj.absolute_url(),
                    "portal_type": obj.portal_type,
                    "type_title": self.get_portal_type_title(obj),
                },
            }
        known = [dic["uid"] for dic in breaches["sources"]]
        for source in sources:
            if IUUID(source) in known:
                continue
            known.append(IUUID(source))
            breaches["sources"].append(
                {
                    "uid": IUUID(source),
                    "title": source.Title(),
                    "url": source.absolute_url(),
                    "accessible": self.is_accessible(source),
                }
            )
        return breaches
