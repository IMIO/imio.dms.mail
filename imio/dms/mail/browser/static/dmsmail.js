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
  $('#batchactions').click(function (e) {
    e.preventDefault();
    var uids = $(".faceted-table-results .select_item_checkbox input:checked").serialize();
    window.location.href = $('base').attr('href') + '/@@batchactions?' + uids
    // $.get($('base').attr('href') + '/@@batchactions', uids, function (json) {});
  });
}

$(document).ready(function(){
    $('#faceted-form #type_widget').click(dmsmail.manage_orgtype_filter);
    $('#formfield-form-widgets-organizations .formHelp').before('<span id="pg-orga-link"><a href="contacts/plonegroup-organization">Lien vers votre organisation</a></span>');
    dmsmail.init_batchactions_button();
});
