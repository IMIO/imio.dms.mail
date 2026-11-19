# -*- coding: utf-8 -*-
from collective.messagesviewlet.utils import add_message
from imio.dms.mail.utils import message_status
from imio.helpers.content import uuidToObject
from imio.helpers.security import check_zope_admin
from persistent.mapping import PersistentMapping
from plone import api
from zope.annotation.interfaces import IAnnotations


DISABLED_OM_TEMPLATES_KEY = "imio.dms.mail.disabled_om_templates"
OM_GENERABLE_TYPES = ("ConfigurablePODTemplate", "MailingLoopTemplate", "PODTemplate")
REMOVED_OM_ADD_ROLES_KEY = "imio.dms.mail.removed_om_add_roles"
OM_ADD_PERMISSION = "collective.dms.mailcontent: Add Outgoing Mail"
OM_ADD_KEPT_ROLES = ("Manager",)
MAINTENANCE_MSG_ID = "om-maintenance"


def om_add_roles(portal):
    """Return the roles having the outgoing mail add permission on the portal."""
    return [dic["name"] for dic in portal.rolesOfPermission(OM_ADD_PERMISSION) if dic["selected"]]


def set_om_add_roles(portal, roles):
    """Set the roles having the outgoing mail add permission on the portal, keeping the acquire setting."""
    portal.manage_permission(OM_ADD_PERMISSION, roles, acquire=bool(portal.acquiredRolesAreUsedBy(OM_ADD_PERMISSION)))


def om_temp_deactivation(self, action=""):
    """Temporarily disable then re-enable the outgoing mail templates and the outgoing mail add permission
    (for all roles except Manager), to prevent any generation or outgoing mail creation.
    A maintenance message is displayed meanwhile.

    :param self: object where the script is called
    :param action: "disable" disables the enabled templates and stores them (can be run again to catch new ones),
                   "enable" re-enables the stored templates. Without action, only the status is displayed.
    """
    if not check_zope_admin():
        return "You must be a zope administrator to run this script"
    self.REQUEST.RESPONSE.setHeader("Content-Type", "text/plain; charset=utf-8")
    portal = api.portal.get()
    annot = IAnnotations(portal)
    om_path = "/".join(portal["templates"]["om"].getPhysicalPath())
    brains = portal.portal_catalog.unrestrictedSearchResults(
        portal_type=OM_GENERABLE_TYPES, path=om_path, sort_on="path"
    )
    out = [u"You can/must call the script with following parameters:",
           u"action=disable => disables the enabled templates and stores them (can be run again to catch new ones),"
           u" removes all roles except Manager from the outgoing mail add permission",
           u" and activates a maintenance message",
           u"action=enable => re-enables the stored templates, re-adds the removed roles"
           u" and deactivates the maintenance message",
           u"Without action, only the status is displayed.",
           u"by example ...?action=enable",
           u""]

    if action == "disable":
        stored = annot.setdefault(DISABLED_OM_TEMPLATES_KEY, PersistentMapping())
        for brain in brains:
            tplt = brain._unrestrictedGetObject()
            if tplt.enabled:
                tplt.enabled = False
                tplt.reindexObject(idxs=["enabled"])  # used by the fancytree template selection
                stored[brain.UID] = brain.getPath()
                out.append(u"Disabled: {}".format(brain.getPath()))
        roles = om_add_roles(portal)
        removed = [role for role in roles if role not in OM_ADD_KEPT_ROLES]
        if removed:
            set_om_add_roles(portal, [role for role in roles if role not in removed])
            annot[REMOVED_OM_ADD_ROLES_KEY] = sorted(set(annot.get(REMOVED_OM_ADD_ROLES_KEY, [])) | set(removed))
            out.append(u"Removed roles on '{}': {}".format(OM_ADD_PERMISSION, u", ".join(removed)))
        if not add_message(
            MAINTENANCE_MSG_ID,
            u"Maintenance courrier sortant",
            u"<p><strong>La création d'un nouveau courrier sortant et la génération depuis un modèle ont été "
            u"désactivées pour maintenance.</strong></p>",
            msg_type="warning",
            req_roles=["Authenticated"],
            activate=True,
        ):  # already existing
            message_status(MAINTENANCE_MSG_ID, to_state="activated", transitions=["activate"])
        out.append(u"Maintenance message activated")
    elif action == "enable":
        stored = annot.pop(DISABLED_OM_TEMPLATES_KEY, {})
        for uid, path in sorted(stored.items(), key=lambda tup: tup[1]):
            tplt = uuidToObject(uid, unrestricted=True)
            if tplt is None:
                out.append(u"Deleted since disabling, ignored: {}".format(path))
                continue
            tplt.enabled = True
            tplt.reindexObject(idxs=["enabled"])
            out.append(u"Enabled: {}".format("/".join(tplt.getPhysicalPath())))
        removed = annot.pop(REMOVED_OM_ADD_ROLES_KEY, [])
        if removed:
            roles = om_add_roles(portal)
            set_om_add_roles(portal, roles + [role for role in removed if role not in roles])
            out.append(u"Re-added roles on '{}': {}".format(OM_ADD_PERMISSION, u", ".join(removed)))
        if message_status(MAINTENANCE_MSG_ID):
            out.append(u"Maintenance message deactivated")
    elif action:
        out.append(u"action parameter must be 'disable' or 'enable'")
        return u"\n".join(out).encode("utf8")
    # status, showing templates created or manually changed since disabling
    stored = annot.get(DISABLED_OM_TEMPLATES_KEY, {})
    out.append(u"Status:")
    out.append(u"Roles having '{}': {} (removed by this script: {})".format(
        OM_ADD_PERMISSION, u", ".join(om_add_roles(portal)),
        u", ".join(annot.get(REMOVED_OM_ADD_ROLES_KEY, [])) or u"none"))
    out.append(u"{} templates stored as disabled by this script:".format(len(stored)))
    for brain in brains:
        tplt = brain._unrestrictedGetObject()
        if tplt.enabled:
            state = u"ENABLED"
        elif brain.UID in stored:
            state = u"disabled by script"
        else:
            state = u"disabled (not handled by script)"
        out.append(u"{}: {}".format(state, brain.getPath()))
    return u"\n".join(out).encode("utf8")
