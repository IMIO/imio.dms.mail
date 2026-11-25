// Collabora edit page (collabora_edit.pt), next to collective.collabora's edit.js.
// Without Collabora autosave, Plone keeps only the save sent by "Save & Close" (overrides._save_on_request
// checks its extended data), so leaving the page any other way drops the changes.

var dms_collabora = {modified: false, leaving: false, closeUrl: null, views: 1};

function dms_collabora_text(name) {
  return document.querySelector(".section-collabora-main").getAttribute(name);
}

function dms_collabora_leave(url) {
  // Collabora unlocks once the page is gone, after uploading: the last user unlocks now, for the page it goes back to
  var actions = document.querySelector(".section-collabora-actions");
  var unlockUrl = actions.getAttribute("data-unlock-url");
  dms_collabora.leaving = true;
  if (!unlockUrl || dms_collabora.views > 1) {
    window.location.href = url;
    return;
  }
  $.post(unlockUrl, {_authenticator: actions.getAttribute("data-authenticator")}).always(function () {
    window.location.href = url;
  });
}

function dms_collabora_save_and_close(link) {
  if (!dms_collabora.modified) {
    dms_collabora_leave(link.href);
    return false;
  }
  dms_collabora.closeUrl = link.href;
  // block editing while saving: a change made after the save snapshot would be lost when leaving
  collabora_postMessage("Action_ShowBusy", {Label: dms_collabora_text("data-saving")});
  collabora_postMessage("Action_Save", {
    DontTerminateEdit: true,
    DontSaveIfUnmodified: false,  // an autosave dropped by Plone leaves the document "unmodified"
    Notify: true,
    ExtendedData: "SaveAndClose=true"
  });
  return false;  // leave once Collabora has saved: it then uploads even if the page is gone
}

function dms_collabora_cancel_and_close(link) {
  dms_collabora_leave(link.href);
  return false;
}

window.addEventListener("message", function (e) {
  var iframe = document.getElementById("cool-iframe");
  if (!iframe || e.source !== iframe.contentWindow) { return; }
  var msg;
  try { msg = JSON.parse(e.data); } catch (err) { return; }
  if (!msg || !msg.Values) { return; }
  if (msg.MessageId === "Views_List") {
    dms_collabora.views = msg.Values.length;  // users in the document, including those who just left
  }
  if (msg.MessageId === "Doc_ModifiedStatus" && msg.Values.Modified) {
    // kept true: a dropped autosave resets Collabora's own status
    dms_collabora.modified = true;
  }
  if (msg.MessageId === "Action_Save_Resp" && dms_collabora.closeUrl) {
    if (msg.Values.success) {
      dms_collabora_leave(dms_collabora.closeUrl);
    } else {
      dms_collabora.closeUrl = null;
      collabora_postMessage("Action_HideBusy");
      window.alert(dms_collabora_text("data-save-error"));
    }
  }
}, false);

window.addEventListener("beforeunload", function (e) {
  var actions = document.querySelector(".section-collabora-actions");
  if (!dms_collabora.modified || dms_collabora.leaving || !actions || actions.getAttribute("data-autosave") === "true") {
    return;
  }
  e.preventDefault();
  e.returnValue = "";  // browsers show their own "changes may not be saved" message
});
