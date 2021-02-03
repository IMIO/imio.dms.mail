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
