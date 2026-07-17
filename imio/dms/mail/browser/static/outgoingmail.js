$(document).ready(function(){

    var url = 'server_sent_events';
    var evtSource = new EventSource(url);
    evtSource.onmessage = function (e) {
      var selectedFileUrl = $('tr.selected').find('.version-link').attr('href');
      var info = JSON.parse(e.data);
      if (info.refresh || selectedFileUrl.endsWith(info.path)) {
        window.location.reload();
      }
    }
/*    evtSource.onerror = function (e) {
      window.alert("Erreur au rafraichissement automatique");
    }*/
});


// Update the sign/approve icons and the invalid-combination warning banner.
// Rebinds the click bound by collective.iconifiedcategory/iconifiedcategory.js.
$(document).ready(function(){
    setTimeout(function() {
    $('a.iconified-action').off('click').on('click', function() {
      var obj = $(this);
      if (!obj.hasClass('editable')) { return false; }
      var values = {'iconified-value': !obj.hasClass('active')};
      $.getJSON(obj.attr('href'), values, function(data) {
        if (data.reload) {  // approval transition happened: full reload
          window.location.reload();
          return;
        }
        // update only the clicked icon (same rules as the base handler)
        if (data.status == 0) {
          obj.removeClass('active').removeClass('deactivated').removeClass('error');
        } else if (data.status == 1) {
          obj.addClass('active').removeClass('deactivated').removeClass('error');
        } else if (data.status == -1) {
          obj.removeClass('active').addClass('deactivated').removeClass('error');
        } else {
          obj.addClass('error');
        }
        obj.attr('alt', data.msg).attr('title', data.msg);
        // AJAX-refresh the invalid-combination warning banner (always-present wrapper)
        if (data.refresh_context_messages) {
          $('#dms-context-messages').load(location.href + ' #dms-context-messages > *');
        }
      });
      return false;
    });
    }, 0);
});
