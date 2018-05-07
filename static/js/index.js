$(main);

function main() {
    $('#register-button').click(registerButtonClicked);
}

function loginButtonClicked() {
    var a = $('#password-form-group');
    if (a.css('display') === 'none') showElement(a, a.prev().css('height'));
    $('#submit').text('Login');
    $('#register-button').text('Register / Forgot password');
    $('form').attr('action', $SCRIPT_ROOT + '/user');
}

function registerButtonClicked() {
    var a = $('#password-form-group');
    if ($(this).text() === 'Login') {
        loginButtonClicked();
        return;
    }
    $('#username-invalid').remove();
    if (a.css('display') !== 'none') hideElement(a);
    $('#submit').text('Register');
    $(this).text('Login');
    $('form').attr('action', $SCRIPT_ROOT + '/activate');
}

function hideElement(e, onComplete) {
    e.animate({height: 0}, {
        duration: 700,
        easing: 'easeInCirc',
        complete: function () {
            e.css('display', 'none');
            $('input', this).attr('type', 'hidden');
            if (onComplete) onComplete();
        }
    });

}

function showElement(e, h, onComplete) {
    e.css('display', 'block');
    e.animate({height: h}, {
        duration: 700,
        easing: 'easeOutCirc',
        complete: function () {
            $('input', this).attr('type', 'password');
            if (onComplete) onComplete();
        }
    });
}
