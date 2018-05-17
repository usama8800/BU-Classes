import os

from flask import *

from defs import *

app = Flask(__name__)
app.jinja_env.line_statement_prefix = '#'


@app.route('/')
def index():
	user_cookie = request.cookies.get('username', False)
	password_cookie = request.cookies.get('hash', False)
	if user_cookie and password_cookie:
		if verify_user(user_cookie, password_cookie):
			return redirect(url_for('user'))
		else:
			resp = make_response(redirect(url_for('index')))
			resp.set_cookie('username', expires = 0)
			resp.set_cookie('password', expires = 0)
			return resp
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


@app.route('/addClass')
def add_class():
	username = request.cookies.get('username', None)
	password = request.cookies.get('hash', None)
	if username and password:
		if verify_user(username, password):
			if 'semester' in request.args and 'college' in request.args and 'department' in request.args and 'course' in request.args and 'section' in request.args:
				insert_class(username, request.args)
		else:
			resp = make_response(redirect(url_for('index')))
			resp.set_cookie('username', expires = 0)
			resp.set_cookie('password', expires = 0)
			return resp
	return redirect(url_for('index'))


@app.route('/logout')
def logout():
	resp = make_response(redirect(url_for('index')))
	resp.set_cookie('username', '', expires = 0)
	resp.set_cookie('password', '', expires = 0)
	return resp


@app.route('/cookie/<name>/<val>')
def cookie(name, val):
	resp = make_response(redirect(url_for('index')))
	resp.set_cookie(name, val)
	return resp


@app.route('/user', methods = ['POST', 'GET'])
def user():
	if request.method == 'POST':
		username = request.form['username']
		salted_pass = get_salted_hash(username, request.form['password'])
		data = get_classes(username, salted_pass)
		if data['error']:
			return redirect(url_for('index', error = data['error'], username = request.form['username']))
		resp = make_response(render_template('username.html', classes = data['classes'], name = data['name']))
		resp.set_cookie('username', username)
		resp.set_cookie('hash', salted_pass)
		return resp
	
	user_cookie = request.cookies.get('username', False)
	password_cookie = request.cookies.get('hash', False)
	if user_cookie and password_cookie and verify_user(user_cookie, password_cookie):
		data = get_classes(user_cookie, password_cookie)
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


@app.route('/removeClass', methods = ['POST', 'GET'])
def remove_class():
	if request.method == 'POST':
		class_ids = request.form.getlist('class_id', None)
		if class_ids:
			delete_class(class_ids)
	return redirect(url_for('user'))


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
