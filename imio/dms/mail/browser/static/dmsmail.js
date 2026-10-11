dmsmail = {};

// the plone bundle makes jQuery global asynchronously: run fn when the DOM is ready and jQuery there
dmsmail.ready = function (fn) {
    if (window.jQuery) {
        jQuery(fn);
    } else {
        window.addEventListener('load', function () { jQuery(fn); });
    }
};

/*
dmsmail.manage_orgtype_filter = function () {
    // show org type widget only when organization type is selected
    var orgtype_widget = $(this).siblings('#orgtype_widget');
    if ($(this).find('#type_organization').prop('checked')) {
        orgtype_widget.show();
    } else {
        orgtype_widget.hide();
    }
};*/

/* onRender of the create from template modal (data-pat-plone-modal): the tree of imio.helpers */
function dmsmailFancytreeModalRendered(modal) {
  var form = $('form#tree-form', modal.$modal);
  if (form.length == 0) {
    return
  }
  if (!$.fn.fancytree) {
    // the fancytree bundle can run before the plone bundle makes jQuery global: load it again
    $.ajax({url: $('script[data-bundle="fancytree"]').attr('src'), dataType: 'script', cache: true})
      .done(function () { dmsmailFancytreeModalRendered(modal); });
    return;
  }
  var submitButton = form.find("input[type='submit']");
  var uidInput = form.find('input[name="uid"]');
  var tree = form.find('#tree');
  var nodes = JSON.parse(tree[0].dataset.nodes);

  form.find('[name="form.buttons.cancel"]').on('click', function () { modal.hide(); });
  submitButton.prop('disabled', true);
  tree.fancytree({
    source: nodes,
    activate: function (event, data) {
      if (!data.node.folder) {
        uidInput.attr('value', data.node.key);
        // native submit: the page goes to the created document
        form[0].submit();
      } else {
        submitButton.prop('disabled', true);
      }
    }
  });
}

function reload_document_with_size(size, percent) {
    if (typeof DV === "undefined" || typeof DV.viewers === "undefined") {
        return;
    }
    var viewer = DV.viewers[window.documentData["id"]];
    if (viewer) {
        viewer.models.document.zoom(size);
        viewer.models.pages.resize();
        viewer.pageSet.redraw();
        var zoomHandle = document.querySelector(".DV-zoomBox .ui-slider-handle");
        if (zoomHandle) {
            zoomHandle.style.left = percent + "%";
        }
    }
}

let dmsmail_dv_container_size = "";

function toggle_dms_document_view(element) {
  /* Toggles CSS to switch between read and normal view */
  const current_view = Cookies.get("dms_document_view") || "view";
  const new_view = current_view === "read" ? "view" : "read";
  Cookies.set("dms_document_view", new_view, { expires: 0.5 }); // 12 hours
  var dv_cont = document.querySelector(".template-view #DV-container");
  if (new_view === "read") {
    document.body.classList.add("read-mode");
    element.classList.add("active");
    if (dv_cont) {
      dmsmail_dv_container_size = dv_cont.style.width;
    }
    reload_document_with_size(1000, "100");
    Cookies.set("dv_zoom_size", 1000, { expires: 0.5 });
  } else {
    document.body.classList.remove("read-mode");
    element.classList.remove("active");
    if (dv_cont && dv_cont.style.width !== dmsmail_dv_container_size) {
        dv_cont.style.width = "100%";
    }
    reload_document_with_size(700, "25");
    Cookies.remove("dv_zoom_size");
  }
}

dmsmail.ready(function(){

    // the css shows the icon of the next state (datagridwidget-row-expanded)
    $(document).on('click', '.datagridwidget-expandable .expand-row-btn', function(e) {
        e.preventDefault();
        var $row = $(this).closest('tr');
        if ($row.hasClass('datagridwidget-empty-row') || $row.hasClass('auto-append')) {
            return;
        }
        var isExpanded = $row.hasClass('datagridwidget-row-expanded');
        $(this).closest('table').find('tr.datagridwidget-row-expanded').removeClass('datagridwidget-row-expanded');
        if (!isExpanded) {
            $row.addClass('datagridwidget-row-expanded');
        }
    });

    /* $('#faceted-form #type_widget').click(dmsmail.manage_orgtype_filter); */

    /* Add sub portaltab menu */
    $('#portaltab-plus a').attr("href", "javascript:void(0)");
    tooltipster_helper('#portaltab-plus a',
                       '@@plus-portaltab-content',
                       [],
                       {position: 'bottom', theme: 'tooltipster-light sub-portaltab', arrow: false,
                        functionPosition_callback: function (instance, helper, position){position.coord.top -= 6;return position;},});

    const current_view = Cookies.get("dms_document_view");
    if (current_view === "read") {
        document.body.classList.add("read-mode");
        $('#read_mode_icon').addClass('active');
        if (typeof DV !== "undefined" && typeof DV.viewers !== "undefined") {
            var viewer = DV.viewers[window.documentData["id"]];
            if (viewer) {
                viewer.onStateChangeCallbacks.push(function() {
                var dv_cont = document.querySelector(".template-view #DV-container");
                if (dv_cont && dmsmail_dv_container_size === "") {
                    dmsmail_dv_container_size = dv_cont.style.width;
                }
                });
            }
        }
    }

    var portal_url = document.body.dataset.portalUrl;
    $('#formfield-form-widgets-organizations .formHelp').before('<span id="pg-orga-link"><a href="' + portal_url + '/contacts/plonegroup-organization" target="_blank">Lien vers mon organisation</a><br /><a href="' + portal_url + '/contacts/personnel-folder" target="_blank">Lien vers mon personnel</a><br /><a href="' + portal_url + '/@@various-utils/kofax_orgs" target="_blank">Listing des services pour Kofax</a></span>');

    // $('body.section-contacts.subsection-personnel-folder #parent-fieldname-title').after('<span id="pers_fold"><a href="cputils_order_folder?key=get_full_name&verbose=">Trier par prénom et nom</a><br /><a href="cputils_order_folder?key=get_sortable_title&verbose=">Trier par nom et prénom</a></span>');

    // replace error message with interpreted html to render links (the message is the text after the <strong>)
    $('.template-usergroup-userprefs .portalMessage.statusmessage-error, .template-usergroup-groupprefs .portalMessage.statusmessage-error').contents().filter(function () {
        return this.nodeType === 3 && this.nodeValue.trim();
    }).replaceWith(function () {
        return $('<span/>').html(this.nodeValue);
    });

    /* remove inline validation for dmsoutgoingmail
    $('.template-dmsoutgoingmail .z3cformInlineValidation, .template-dmsdocument-edit.portaltype-dmsoutgoingmail .z3cformInlineValidation').removeClass('z3cformInlineValidation'); */

    $('a.iconified-action-approved').click(function() {
    var obj = $(this);
    if (!obj.hasClass('editable')) {
      return false;
    }
    var values = {'iconified-value': !obj.hasClass('active')};
    $.getJSON(
      obj.attr('href'),
      values,
      function(data) {
        window.location.reload();
        return;
      }
    );
    return false;
    });

});
