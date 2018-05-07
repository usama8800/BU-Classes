import os

from flask import *

from defs import *

app = Flask(__name__)
app.jinja_env.line_statement_prefix = '#'
app.config.update(TEMPLATES_AUTO_RELOAD = True)


@app.route('/')
def index():
	username = request.args.get('username', False)
	error = request.args.get('error', False)
	user_error = False
	pass_error = False
	if error:
		error = eval(error)
		if 'user' in error:
			user_error = error['user']
		if 'pass' in error:
			pass_error = error['pass']
	return render_template('index.html', username = username, user_error = user_error, pass_error = pass_error)


@app.route('/user', methods = ['POST', 'GET'])
def user():
	if request.method == 'POST':
		data = get_classes(request.form['username'], request.form['password'])
		if data['error']:
			return redirect(url_for('index', error = data['error'], username = request.form['username']))
		return render_template('username.html', classes = data['classes'], name = data['name'])
	return redirect(url_for('index'))


@app.route('/activate', methods = ['POST', 'GET'])
def activate():
	if request.method == 'POST':
		username = request.form['username']
		if len(username) == 0:
			return redirect(url_for('index'))
		code = add_activation(username)
		send_activation_email(username, url_for('register', _external = True, code = code))
		return render_template('activate.html', username = username)
	else:
		return redirect(url_for('index'))


@app.route('/register', defaults = {'code': None}, methods = ['POST', 'GET'])
@app.route('/register/<code>')
def register(code):
	if code:
		activation = get_activation(code)
		if activation:
			user_ = get_user(activation[1])
			data = {'username': activation[1]}
			if user_:
				data['name'] = user_[1]
			return render_template('register.html', data = data)
		return redirect(url_for('index'))
	if request.method == 'POST':
		if request.form['password'] != request.form['confirm-password']:
			redirect(url_for('index'))
		if 'old' not in request.form:
			if not exists_activation(request.form['username']) or get_user(request.form['username']):
				redirect(url_for('index'))
			create_user(request.form['username'], request.form['name'], request.form['password'])
			return render_template('registered.html', message = "<span class='em'>%s</span> registered" % request.form['username'])
		if not get_user(request.form['username']):
			redirect(url_for('index'))
		update_password(request.form['username'], request.form['password'])
		return render_template('registered.html', message = "Password reset for <span class='em'>%s</span>" % request.form['username'])
	return redirect(url_for('index'))


@app.context_processor
def override_url_for():
	return dict(url_for = dated_url_for)


def dated_url_for(endpoint, **values):
	if endpoint == 'static':
		filename = values.get('filename', None)
		if filename:
			file_path = os.path.join(app.root_path, endpoint, filename)
			values['q'] = int(os.stat(file_path).st_mtime)
	return url_for(endpoint, **values)


if __name__ == "__main__":
	app.run(debug = True)
