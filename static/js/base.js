$(main);

function main() {
    $('#logout').on('click', logout);
}

function logout() {
    $('#logout-form').submit();
}
