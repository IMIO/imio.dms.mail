dmsmail = {};

dmsmail.manage_orgtype_filter = function () {
    // show org type widget only when organization type is selected
    var orgtype_widget = $(this).siblings('#orgtype_widget');
    if ($(this).find('#type_organization').prop('checked')) {
        orgtype_widget.show();
    } else {
        orgtype_widget.hide();
    }
};

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
    dmsmail.initializeOverlays('#'+form_id);
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
dmsmail.initialize_fancytree = function () {
  var submitButton = $("#tree-form input[type='submit'");
  var uidInput = $('#tree-form input[name="uid"]');
  var nodes = JSON.parse(document.getElementById('tree').dataset.nodes);

  submitButton.prop('disabled', true);
  $('#tree').fancytree({
    source: nodes,
    activate: function (event, data) {
      if (!data.node.folder) {
        uidInput.attr('value', data.node.key);
        submitButton.prop('disabled', false);
      } else {
        submitButton.prop('disabled', true);
      }
    }
  });
}

$(document).ready(function(){

    var url = 'server_sent_events';
    var evtSource = new EventSource(url);
    evtSource.onmessage = function (e) {
      var selectedFileUrl = $('tr.selected').find('.version-link').attr('href');
      var info = JSON.parse(e.data);
      if (info.justAdded || selectedFileUrl.endsWith(info.path)) {
        window.location.reload();
      }
    }

    $('#faceted-form #type_widget').click(dmsmail.manage_orgtype_filter);
    $('#formfield-form-widgets-organizations .formHelp').before('<span id="pg-orga-link"><a href="contacts/plonegroup-organization" target="_blank">Lien vers mon organisation</a><br /><a href="contacts/personnel-folder" target="_blank">Lien vers mon personnel</a></span>');

    $('.overlay').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]'
    });

    // replace error message with interpreted html to render links
    $('.template-usergroup-userprefs .portalMessage.error dd, .template-usergroup-groupprefs .portalMessage.error dd').html(function(index, html){
        return $("<div/>").html(html).text();

})

    /* remove inline validation for dmsoutgoingmail
    $('.template-dmsoutgoingmail .z3cformInlineValidation, .template-dmsdocument-edit.portaltype-dmsoutgoingmail .z3cformInlineValidation').removeClass('z3cformInlineValidation'); */

/*    $(document).bind('loadInsideOverlay', function(e, el, responseText, errorText, api) {
        dmsmail.initialize_fancytree();
    });*/

});
