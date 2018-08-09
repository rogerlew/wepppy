//https://ourcodeworld.com/articles/read/143/how-to-copy-text-to-clipboard-with-javascript-easily

function setClipboardText(text) {
    var id = "mycustom-clipboard-textarea-hidden-id";
    var existsTextarea = document.getElementById(id);

    if(!existsTextarea){
        console.log("Creating textarea");
        var textarea = document.createElement("textarea");
        textarea.id = id;
        // Place in top-left corner of screen regardless of scroll position.
        textarea.style.position = 'fixed';
        textarea.style.top = '0';
        textarea.style.left = '0';

        // Ensure it has a small width and height. Setting to 1px / 1em
        // doesn't work as this gives a negative w/h on some browsers.
        textarea.style.width = '1px';
        textarea.style.height = '1px';

        // We don't need padding, reducing the size if it does flash render.
        textarea.style.padding = '0';

        // Clean up any borders.
        textarea.style.border = 'none';
        textarea.style.outline = 'none';
        textarea.style.boxShadow = 'none';

        // Avoid flash of white box if rendered for any reason.
        textarea.style.background = 'transparent';
        document.querySelector("body").appendChild(textarea);
        //console.log("The textarea now exists :)");
        existsTextarea = document.getElementById(id);
    }else{
        //console.log("The textarea already exists :3")
    }

    existsTextarea.value = text;
    existsTextarea.select();

    try {
        var status = document.execCommand('copy');
        if(!status){
            console.error("Cannot copy text");
            return 0;
        }else{
            //console.log("The text is now on the clipboard");
            return 1;
        }
    } catch (err) {
        console.log('Unable to copy.');
        return 0;
    }
}

function _fmt(s) {
    return s.replace('&nbsp;', '')
            .replace('</sup>', '')
            .replace('<sup>', '^')
}

function copytable(tbl_id) {

    var rows = $('tr', '#' + tbl_id);

    var text = [];
    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];

        var rowtext = [];
        for (var j = 0; j < row.children.length; j++) {
            var cell = row.children[j];

        if (cell.children.length === 0) {
                //console.log(i, j, cell.innerHTML);
                rowtext.push(_fmt(cell.innerHTML));
        } else {
                for (var k = 0; k < cell.children[0].children.length; k++) {
                    if (!cell.children[0].children[k].classList.contains('invisible')) {
                        //console.log(i, j, cell.children[0].children[k].innerHTML);
                        rowtext.push(_fmt(cell.children[0].children[k].innerHTML));
                    }
                }
            }
        }

        text.push(rowtext.join('\t'));
    }

    text = text.join('\n');

    var title = $('#' + tbl_id).prev()[0].innerHTML;
    var i = title.indexOf("<a onclick");
    if (i > 0) {
        text = title.substring(0, i).split(/\s+/).join(' ') + '\n' + text;
    }

    //console.log(text)
    var status = setClipboardText(text);

    if (status === 1) {
        alert(tbl_id + ' copied to clipboard');
    } else {
        alert('Error copying ' + tbl_id + ' to clipboard');
    }
}