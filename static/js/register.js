$(main);

function main() {
    $('[type=password]').keyup(passwordChanged);
}

function passwordChanged() {
    var a = $('[name=password]');
    var b = $('[name=confirm-password]');
    if (a[0].validity.valid) {
        if (a.val() !== b.val()) {
            b[0].setCustomValidity("Must match the password above");
        } else {
            b[0].setCustomValidity("");
        }
    }
}
