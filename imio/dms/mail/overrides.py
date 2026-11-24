# -*- coding: utf-8 -*-
#
# File: overrides.py
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass
from AccessControl.SecurityManagement import getSecurityManager
from Acquisition import aq_base
from collective.collabora.browser.edit import CollaboraEditView
from collective.collabora.browser.wopi import CollaboraWOPIView
from collective.contact.plonegroup.subscribers import PloneGroupContactChecksAdapter
from collective.contact.plonegroup.subscribers import search_value_in_objects
from collective.task.adapters import TaskContentAdapter
from imio.dms.mail.utils import COLLABORA_LOCK
from imio.dms.mail.utils import COLLABORA_LOCK_ID
from imio.dms.mail.utils import get_collabora_lock_id
from imio.dms.mail.utils import get_dms_config
from imio.dms.mail.utils import is_collabora_read_only
from logging import getLogger
from plone import api
from plone.locking.interfaces import ILockable
from plone.locking.interfaces import ITTWLockable
from plone.memoize.view import memoize
from plone.protect.interfaces import IDisableCSRFProtection
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService
from zope.annotation.interfaces import IAnnotations
from zope.interface import alsoProvides

import json
import os


logger = getLogger("imio.dms.mail.overrides")
# Path segment that identifies Collabora's own server-to-server callback.
COLLABORA_CALLBACK = "@@collabora-wopi"
# Extended data sent with the save of our "Save & Close" button (collabora_edit.js).
COLLABORA_SAVE_REQUEST = "SaveAndClose=true"


class DmsPloneGroupContactChecksAdapter(PloneGroupContactChecksAdapter):
    def check_items_on_delete(self):
        fields = {
            "dmsincomingmail": ["treating_groups", "recipient_groups"],
            "dmsincoming_email": ["treating_groups", "recipient_groups"],
            "dmsoutgoingmail": ["treating_groups", "recipient_groups"],
            "task": ["assigned_group", "enquirer", "parents_assigned_groups", "parents_enquirers"],
        }
        search_value_in_objects(self.context, self.context.UID(), p_types=fields.keys(), type_fields=fields)

    def check_items_on_transition(self):
        fields = {
            "dmsincomingmail": ["treating_groups", "recipient_groups"],
            "dmsincoming_email": ["treating_groups", "recipient_groups"],
            "dmsoutgoingmail": ["treating_groups", "recipient_groups"],
            "task": ["assigned_group", "enquirer", "parents_assigned_groups", "parents_enquirers"],
        }
        search_value_in_objects(self.context, self.context.UID(), p_types=fields.keys(), type_fields=fields)


class DmsTaskContentAdapter(TaskContentAdapter):
    security = ClassSecurityInfo()

    security.declarePublic("can_do_transition")

    def can_do_transition(self, transition):
        """Check if assigned_user is set or if the test is required or if the user is admin.
        Used in guard expression for n+1 related task transitions
        """
        if self.context.assigned_group is None:
            # print "no tg: False"
            return False
        way_index = transition.startswith("back_in") and 1 or 0
        # show only the next valid level
        state = api.content.get_state(self.context)
        transitions_levels = get_dms_config(["transitions_levels", "task"])
        if (
            self.context.assigned_group in transitions_levels[state]
            and transitions_levels[state][self.context.assigned_group][way_index] == transition
        ):
            # print "from state: True"
            return True
        return False


InitializeClass(DmsTaskContentAdapter)


def _record_async_user_folder():
    """Queue async jobs against the acl_users that really holds the user.

    Collabora's WOPI callback runs the Zope root admin against the site
    acl_users, which does not know it, so the worker could not restore the user
    and no preview was rebuilt (DMS-1227).
    """
    try:
        from plone.app.async import service  # noqa E999
    except ImportError:
        # No async at all, as in the dev buildout: conversions run inline.
        logger.debug("plone.app.async not available; skipping async user patch.")
        return

    original = service._getAuthenticatedUser

    def _getAuthenticatedUser():
        """Same as upstream, but fall back to the Zope root acl_users."""
        uf_path, user_id = original()
        if not uf_path:
            return uf_path, user_id
        acl_users = getSecurityManager().getUser().aq_parent
        if acl_users.getUserById(user_id) is not None:
            return uf_path, user_id
        root_uf = getattr(acl_users.getPhysicalRoot(), "acl_users", None)
        if root_uf is None or root_uf.getUserById(user_id) is None:
            # Unknown everywhere: leave it, so the worker says so plainly.
            return uf_path, user_id
        logger.info(
            "User %r is unknown to %r but is a Zope root user: queueing the "
            "job against the root acl_users.",
            user_id,
            "/".join(uf_path),
        )
        return root_uf.getPhysicalPath(), user_id

    service._getAuthenticatedUser = _getAuthenticatedUser


def _authenticate_zope_root_user():
    """Let a Zope root account edit through Collabora, not only files it owns.

    Collabora reads and writes the document from its own server, authenticated
    with a token minted for the browsing user id. The site acl_users does not
    know a Zope root account such as "admin", but plone.restapi's token plugin
    returns the id anyway, so PAS builds a user holding only the Authenticated
    role. The callback then reads only the files that account happens to own
    (Owner local role) and Plone answers the login form for every other one, which
    Collabora shows as an empty frame (DMS-1228). Hand back the real Zope root
    user instead: that is the identity the browser session already runs under.

    Restricted to Collabora's own callback, so no other lookup changes.
    """
    original = PluggableAuthService._findUser

    def _findUser(self, plugins, user_id, name=None, request=None):
        """Same as upstream, but resolve a Zope root account for that callback."""
        user = original(self, plugins, user_id, name=name, request=request)
        if request is None or COLLABORA_CALLBACK not in (request.get("PATH_INFO") or ""):
            return user
        if self.getUserById(user_id) is not None:
            return user  # a real member of this site: upstream already got it right
        root_uf = getattr(self.getPhysicalRoot(), "acl_users", None)
        if root_uf is None or root_uf.getUserById(user_id) is None:
            # Unknown everywhere: leave it, so the request fails as it would have.
            return user
        logger.info(
            "%r is unknown to %r but is a Zope root user: running Collabora's "
            "callback as that root user.",
            user_id,
            "/".join(self.getPhysicalPath()),
        )
        return root_uf.getUserById(user_id)

    # beware if imio.helpers decorates _findUser (commented now), it will not decorate the right method if applied here
    PluggableAuthService._findUser = _findUser


def _allow_localhost_dev():
    """Drop upstream's localhost guard on plone_server_url (dev only).

    Our dev container runs with network_mode: host, so that guard is a false positive there.
    """

    def plone_server_url(self):
        """Same as upstream, minus the localhost guard."""
        return api.portal.get_registry_record("collective.collabora.plone_server_url", default=None) or self.portal_url

    CollaboraEditView.plone_server_url = property(memoize(plone_server_url))
    logger.warning("COLLABORA_DEV_MODE set: allowing localhost plone_server_url (dev only, network_mode: host).")


def _hide_collabora_popups():
    """Hide Collabora's welcome popup and onboarding tour.

    Its client skips the popup for guests, and the tour once the user settings (@@collabora-settings) mark it
    as seen. The CODE server can only disable them with home_mode, which caps connections.
    """
    file_info = CollaboraWOPIView.file_info.fget
    call = CollaboraWOPIView.__call__

    def popup_file_info(self):
        """Same as upstream, flagged as guest, with our user settings."""
        info = file_info(self)
        info["UserExtraInfo"] = {"is_guest": True}
        info["UserSettings"] = {"uri": api.portal.get().absolute_url() + "/@@collabora-settings", "stamp": "1"}
        return info

    def call_without_settings_upload(self):
        """Same as upstream, but drop the user settings uploads: user prefs stay in the browser."""
        if self.request.get("PATH_INFO", "").endswith(COLLABORA_CALLBACK + "/settings/upload"):
            return ""
        return call(self)

    CollaboraWOPIView.file_info = property(popup_file_info)
    CollaboraWOPIView.__call__ = call_without_settings_upload


def _lock_collabora_edition():
    """Lock a file while Collabora edits it, so others can edit neither the file nor its metadata.

    Collabora locks when its first writer opens the document, refreshes the lock and unlocks at the end. Others open
    it read-only, unless collaborative editing is enabled. The ILocking behavior protects the metadata edit form.
    """
    file_info = CollaboraWOPIView.file_info.fget
    call = CollaboraWOPIView.__call__
    put_file = CollaboraWOPIView.wopi_put_file

    def lock_file_info(self):
        """Same as upstream, with locks, read-only while another user edits the file."""
        info = file_info(self)
        if ITTWLockable.providedBy(self.context):
            info["SupportsLocks"] = True
            info["SupportsGetLock"] = True
            info["UserCanWrite"] = info["UserCanWrite"] and not is_collabora_read_only(self.context)
        return info

    def call_with_locks(self):
        """Same as upstream, plus the WOPI Lock, RefreshLock, Unlock and GetLock operations."""
        operation = self.request.get_header("X-WOPI-Override")
        if (
            self.wopi_mode != "file_info"
            or operation not in ("LOCK", "REFRESH_LOCK", "UNLOCK", "GET_LOCK")
            or not ITTWLockable.providedBy(self.context)
        ):
            return call(self)
        if operation != "GET_LOCK" and not self.can_edit:
            self.request.response.setStatus(403)
            return ""
        alsoProvides(self.request, IDisableCSRFProtection)
        lock_id = self.request.get_header("X-WOPI-Lock", "")
        lockable = ILockable(self.context)
        current = get_collabora_lock_id(self.context)
        if operation == "LOCK" and current is None and not lockable.locked():
            lockable.lock(COLLABORA_LOCK)
            IAnnotations(self.context)[COLLABORA_LOCK_ID] = lock_id
        elif operation in ("LOCK", "REFRESH_LOCK") and current == lock_id:
            lockable.refresh_lock(COLLABORA_LOCK)
        elif operation == "UNLOCK" and current == lock_id:
            lockable.unlock(COLLABORA_LOCK, stealable_only=False)
            del IAnnotations(self.context)[COLLABORA_LOCK_ID]
        elif operation != "GET_LOCK":
            self.request.response.setStatus(409)  # Collabora then opens the document read-only
        self.request.response.setHeader("X-WOPI-Lock", current or "")
        return ""

    def put_file_with_lock(self):
        """Same as upstream, but refuse a save from another Collabora session than the lock holder."""
        current = get_collabora_lock_id(self.context) if ITTWLockable.providedBy(self.context) else None
        if current is not None and self.request.get_header("X-WOPI-Lock") != current:
            self.request.response.setStatus(409)
            self.request.response.setHeader("X-WOPI-Lock", current)
            return ""
        return put_file(self)

    CollaboraWOPIView.file_info = property(lock_file_info)
    CollaboraWOPIView.__call__ = call_with_locks
    CollaboraWOPIView.wopi_put_file = put_file_with_lock


def _save_on_request():
    """Keep only the saves asked by our "Save & Close" button, unless Collabora autosave is enabled.

    Collabora also saves by itself (when idle, every minute while editing, when leaving): those saves are dropped, so
    "Cancel & Close" discards the changes. Collabora's own save button is hidden.
    """
    file_info = CollaboraWOPIView.file_info.fget
    put_file = CollaboraWOPIView.wopi_put_file

    def autosave():
        return api.portal.get_registry_record(
            "imio.dms.mail.browser.settings.IImioDmsMailConfig.collabora_autosave", default=False
        )

    def save_file_info(self):
        """Same as upstream, without Collabora's own save button."""
        info = file_info(self)
        if not autosave():
            info["HideSaveOption"] = True
        return info

    def wopi_put_file(self):
        """Same as upstream, but drop the saves not asked by "Save & Close"."""
        if autosave() or COLLABORA_SAVE_REQUEST in (self.request.get_header("X-COOL-WOPI-ExtendedData") or ""):
            # a preview completed before this save is outdated: wait for the next one (ServerSentEvents)
            if getattr(aq_base(self.context), "conversion_finished", False):
                del self.context.conversion_finished
            return put_file(self)
        logger.info("Dropped a Collabora save not asked by Save & Close on %r", self.context.absolute_url())
        self.request.response.setHeader("Content-Type", "application/json")
        return json.dumps(self.file_info)

    CollaboraWOPIView.file_info = property(save_file_info)
    CollaboraWOPIView.wopi_put_file = wopi_put_file


_record_async_user_folder()
_authenticate_zope_root_user()
_hide_collabora_popups()
_lock_collabora_edition()
_save_on_request()
if os.environ.get("COLLABORA_DEV_MODE"):
    _allow_localhost_dev()
