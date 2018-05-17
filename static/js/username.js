$(main);

function main() {
    $('input[type=text]').on('input', makeCap);
    $('#remove-button').click(removeButtonClicked);
    debug()
}

function removeButtonClicked() {
    $('#remove-form').submit();
}

function makeCap() {
    $(this).val($(this).val().toUpperCase());
}

function debug() {
    $('[value=20193]').attr('selected', '');
    $('[value=CAS]').attr('selected', '')
    $('[name=department]').val('CS');
    $('[name=course]').val('237');
}
