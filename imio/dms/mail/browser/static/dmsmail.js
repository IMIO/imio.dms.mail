dmsmail = {};

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

dmsmail.init_batchactions_button = function () {

  /*var glob_sel = $('input#select_unselect_items');
  if( glob_sel[0] !== undefined && glob_sel[0].checked ) {
    glob_sel[0].checked = false;
    $('input[name="select_item"').attr('checked', false);
  }*/
  if ( $('.faceted-table-results')[0] == undefined ) {
    $('#dashboard-batch-actions').hide();
  }

  $('.batch-action-but').click(function (e) {
    e.preventDefault();
    var uids = selectedCheckBoxes('select_item');
    if (!uids.length) { alert('Aucun élément sélectionné'); return;}
    var referer = document.location.href.replace('#','!').replace(/&/g,'@');
    var ba_form = $(this).parent()[0];
    var form_id = ba_form.id;
    if(typeof document.batch_actions === "undefined") {
        document.batch_actions = [];
    }
    if(document.batch_actions[form_id] === undefined) {
        document.batch_actions[form_id] = ba_form.action;
    }
    var uids_input = $(ba_form).find('input[name="uids"]');
    if (uids_input.length === 0) {
        uids_input = $('<input type="hidden" name="uids" value="" />');
        $(ba_form).append(uids_input);
    }
    uids_input.val(uids);
    ba_form.action = document.batch_actions[form_id] + '?referer=' + referer;

    if (form_id != 'reply-batch-action') {
        dmsmail.initializeOverlays('#'+form_id);
    }
    else {
        ba_form.submit();
    }
  });
};

dmsmail.initializeOverlays = function (form_id) {
    // Add batch actions popup
    $(form_id).prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]'
    });
};

/* we have to copy this from imio.helpers to make it work in overlays */
/* create from template tree */
dmsmail.initialize_fancytree = function () {
  if ($("form#tree-form").length == 0) {
    return
  }
  var submitButton = $("#tree-form input[type='submit'");
  var uidInput = $('#tree-form input[name="uid"]');
  var nodes = JSON.parse(document.getElementById('tree').dataset.nodes);

  submitButton.prop('disabled', true);
  $('#tree').fancytree({
    source: nodes,
    activate: function (event, data) {
      if (!data.node.folder) {
        uidInput.attr('value', data.node.key);
        // submitButton.prop('disabled', false);
        $("div.overlay div.close").click();
        $("#tree-form").submit();
      } else {
        submitButton.prop('disabled', true);
      }
    }
  });
}

$(document).ready(function(){

    /* Remove this overlay causing error in overlayhelpers and ckeditor not loading */
    $('.template-atct_edit.portaltype-document #atrb_relatedItems').remove();
    /* $('#faceted-form #type_widget').click(dmsmail.manage_orgtype_filter); */

    /* Add sub portaltab menu */
    $('#portaltab-plus a').attr("href", "javascript:void(0)");
    tooltipster_helper(selector='#portaltab-plus a',
                       view_name='@@plus-portaltab-content',
                       data_parameters=[],
                       options={position: 'bottom', theme: 'tooltipster-light sub-portaltab', arrow: false,
                       functionPosition_callback: function (instance, helper, position){position.coord.top -= 6;return position;},});

    $('#formfield-form-widgets-organizations .formHelp').before('<span id="pg-orga-link"><a href="contacts/plonegroup-organization" target="_blank">Lien vers mon organisation</a><br /><a href="contacts/personnel-folder" target="_blank">Lien vers mon personnel</a><br /><a href="@@various-utils/kofax_orgs" target="_blank">Listing des services pour Kofax</a></span>');

    // $('body.section-contacts.subsection-personnel-folder #parent-fieldname-title').after('<span id="pers_fold"><a href="cputils_order_folder?key=get_full_name&verbose=">Trier par prénom et nom</a><br /><a href="cputils_order_folder?key=get_sortable_title&verbose=">Trier par nom et prénom</a></span>');

    // replace error message with interpreted html to render links
    $('.template-usergroup-userprefs .portalMessage.error dd, .template-usergroup-groupprefs .portalMessage.error dd').html(function(index, html){
        return $("<div/>").html(html).text();})

    /* remove inline validation for dmsoutgoingmail
    $('.template-dmsoutgoingmail .z3cformInlineValidation, .template-dmsdocument-edit.portaltype-dmsoutgoingmail .z3cformInlineValidation').removeClass('z3cformInlineValidation'); */


/* Added with first version of create form template on im r22564 */
    $('.overlay').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]'
    });

    $(document).bind('loadInsideOverlay', function(e, el, responseText, errorText, api) {
        dmsmail.initialize_fancytree();
    });

});
