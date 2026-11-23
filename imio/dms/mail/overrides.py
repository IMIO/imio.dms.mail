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
from collective.collabora.browser.edit import CollaboraEditView
from collective.contact.plonegroup.subscribers import PloneGroupContactChecksAdapter
from collective.contact.plonegroup.subscribers import search_value_in_objects
from collective.task.adapters import TaskContentAdapter
from imio.dms.mail.utils import get_dms_config
from logging import getLogger
from plone import api
from plone.memoize.view import memoize
from Products.PluggableAuthService.PluggableAuthService import PluggableAuthService

import os


logger = getLogger("imio.dms.mail.overrides")
# Path segment that identifies Collabora's own server-to-server callback.
COLLABORA_CALLBACK = "@@collabora-wopi"


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


_record_async_user_folder()
_authenticate_zope_root_user()
if os.environ.get("COLLABORA_DEV_MODE"):
    _allow_localhost_dev()
