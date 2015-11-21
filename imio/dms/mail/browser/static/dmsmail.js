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

  var glob_sel = $('input#select_unselect_items');
  if( typeof glob_sel !== undefined && glob_sel[0].checked ) {
    glob_sel[0].checked = false;
    $('input[name="select_item"').attr('checked', false);
  }

  $('#transition-batch-action-but').click(function (e) {
    e.preventDefault();
    var uids = selectedCheckBoxes('select_item');
    if (!uids.length) { alert('Aucun élément sélectionné'); return;}
    var ba_form = document.getElementById('transition-batch-action');
    var form_id = ba_form.id;
    if(typeof document.batch_actions === "undefined") {
        document.batch_actions = [];
    }
    if(document.batch_actions[form_id] === undefined) {
        document.batch_actions[form_id] = ba_form.action;
    }
    ba_form.action = document.batch_actions[form_id] + '?uids=' + uids;
    dmsmail.initializeOverlays();
  });
};

dmsmail.initializeOverlays = function () {
    // Add batch actions popup
    $('#transition-batch-action').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]'
    });
};
        
$(document).ready(function(){
    $('#faceted-form #type_widget').click(dmsmail.manage_orgtype_filter);
    $('#formfield-form-widgets-organizations .formHelp').before('<span id="pg-orga-link"><a href="contacts/plonegroup-organization">Lien vers votre organisation</a></span>');
});
