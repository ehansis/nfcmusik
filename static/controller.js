// reload list of music files and render it
function refreshMusicFiles() {
    $.getJSON('json/musicfiles', function(data) {
        var fileList = $("#musicFiles");

        fileList.empty();

        $.each(data, function(i, f) {
            var li = $('<li/>')
                .attr('id', f.hash)
                .addClass('musicFileItem')
                .text(f.name + '   ')
                .appendTo(fileList);

            var href = $('<button/>')
                .attr('type', 'button')
                .addClass("btn btn-default")
                .click(function() { writeNFC(f.hash); })
                .text('write to tag')
                .appendTo(li);
        });
    });
}

// reload list of VLC actions and render it
function refreshVLCActions() {
    $.getJSON('json/vlcactions', function(data) {
        var fileList = $("#vlcActions");

        fileList.empty();

        $.each(data, function(i, f) {
            var li = $('<li/>')
                .attr('id', f.hash)
                .addClass('musicFileItem')
                .text(f.name + '   ')
                .appendTo(fileList);

            var href = $('<button/>')
                .attr('type', 'button')
                .addClass("btn btn-default")
                .click(function() { writeNFC(f.hash); })
                .text('write to tag')
                .appendTo(li);
        });
    });
}


function writeNFC(data) {
    $.getJSON('actions/writenfc?data=' + data, function(ret) {
        setStatus(ret.message);
    });
}


function setStatus(status) {
    var statusBox = $('#statusBox');
    
    statusBox.empty();

    $('<p/>')
        .text('Status: ' + status)
        .appendTo(statusBox);
}


function pollNFC(){
    $.getJSON('json/readnfc', function(data) {

        var nfcStatus = $('#nfcStatusBox');

        nfcStatus.empty();

        $('<p/>')
            .text('NFC Tag Status: ' + data['description'] + ' (UID:' + data['uid'] + ', data: ' + data['data'] + ')')
            .appendTo(nfcStatus);

        // poll again in 1 sec
        setTimeout(pollNFC, 1000);
    });
}

