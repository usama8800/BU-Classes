import hashlib
import random
import sqlite3
import time
import unicodedata
from os import path

import requests
import sendgrid
from bs4 import BeautifulSoup
from sendgrid.helpers.mail import *

main_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/uismpl/1204835367?ModuleName=univschs.pl"
search_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/1510675812?ModuleName=univschr.pl&SearchOptionDesc=Class+Number&SearchOptionCd=S&KeySem=%s&College=%s&Dept=%s&Course=%s&Section=%s&MainCampusInd=%s"
indexes = {'Class': 0, 'Title': 1, 'Credits': 3, 'Type': 4, 'Seats': 5, 'Building': 6, 'Room': 7, 'Day': 8, 'Start': 9, 'Stop': 10, 'Notes': 11}
ROOT = path.dirname(path.realpath(__file__))


def log(arg=''):
	print(arg)
	with open('log.txt', 'a') as f:
		f.write(arg + '\n')


def get(record, index, i=-1):
	if i == -1:
		if len(record[indexes[index]]) == 1:
			return record[indexes[index]][0]
		return record[indexes[index]]
	if i < len(record[indexes[index]]):
		return record[indexes[index]][i]
	return ''


def search_classes(class_info, verbose=True):
	"""
	:param class_info: SemCode, College, Dept, Course, Section
	:param verbose:
	"""
	section = class_info[4]
	crco = 'N'
	data = []
	while True:
		info = []
		custom_url = search_url % (class_info[0], class_info[1], class_info[2], class_info[3], section, crco)  # Create the custom URL with the user values
		try:
			# raise IndexError
			soup = BeautifulSoup(str(requests.get(custom_url).text), "html.parser")  # Get the text from the URL and parse it
		except Exception:
			return [[[class_info[1] + ' ' + class_info[2] + class_info[3] + ' ' + class_info[4]], [class_info[4] + ' Title'], None, ['4.0'], ['Lecture'], ['42'], ['CAS'], ['B23'], ['Wed'], ['8:15 am'], ['9:05 am'], ['']]]
		if len(soup.find_all('table')) < 6:
			print(soup)
			break
		soup = BeautifulSoup(str(soup.find_all('table')[5]), "html.parser")  # Parse the 6th table which contains the class list
		for i, tr in enumerate(soup.find_all('tr')):
			record = []
			for j, td in enumerate(tr.find_all(['td', 'th'])):
				if j == 0:  # First item is always empty
					continue
				td = str(td.get_text(separator = ';', strip = True))  # gets the text with ; in between if there is more than one line
				td = unicodedata.normalize("NFKD", td)  # Convert the unicode characters to utf-8
				td = td.split(';')  # Split the td into lines
				td = [item for item in td if str(item)]  # Get rid of empty strings
				record.append(td)  # Add field to record
			if len(record) == 12 and (i != 0 or section == ''):  # Don't add the rows which are not classes and don't add the header row
				#  for second page
				data.append(record)  # Checks if we need to go to the next page for more classes and filter the classes
		done = True
		for record in data:
			cls = get(record, 'Class')  # Get the class - CAS CS112 A1
			if (class_info[2] not in cls or class_info[3] not in cls or (class_info[4] != '' and class_info[4] not in cls[-2:])) and cls != 'Class':
				done = True
			else:
				done = False
				if get(record, 'Class') == 'Class':
					continue
				if not verbose:  # Filter out rows with 0 classes if set to it
					if get(record, 'Seats') != '0':
						info.append(record)
				else:
					info.append(record)
				section = cls[-2:]  # Change section for the next page
		if done:
			break
	
	return info


def get_classes(username, password):
	"""
	:param username: string
	:param password: salted password
	"""
	user = get_user(username)
	if not user:
		return {'error': {'user': 'User not found'}}
	if not verify_user(username, password):
		return {'error': {'pass': 'Invalid password'}}
	
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	c.execute('SELECT * FROM classes WHERE user=?', (user[0],))
	records = c.fetchall()
	conn.close()
	classes = []
	for record in records:
		if record[-1] == 1:
			continue
		searched = search_classes(record[2:-1])
		for cls in searched:
			cls.append(record[0])
		classes += searched
	return {'classes': classes, 'name': user[1], 'error': False}


def check_password(user, password):
	"""
	Checks if password matches
	:param user: user object from sql
	:param password: unhashed string
	"""
	return user[2] == sha3(password + str(user[3]))


def get_salted_hash(username, password):
	"""
	Returns a hash salted with users salt
	:param username: string
	:param password: unhashed string
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	c.execute('SELECT * FROM users WHERE username=?', (username,))
	user = c.fetchone()
	conn.close()
	if user:
		return sha3(password + str(user[3]))


def verify_user(username, password):
	"""
	Checks username and hash given with username and salted hashed password in database
	:param username: string
	:param password: salted hashed password
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	c.execute('SELECT * FROM users WHERE username=?', (username,))
	user = c.fetchone()
	conn.close()
	if user:
		return password == user[2]


def get_user(username):
	"""
	:param username: string
	:return: user object from sql
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	c.execute('SELECT * FROM users WHERE username=?', (username,))
	user = c.fetchone()
	conn.close()
	return user


def get_activation(code):
	"""
	Returns if activation code found in database when user clicks on activation link in email
	:param code: activation hash
	:return: sql object
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	c.execute('SELECT * FROM activations WHERE code=?', (code,))
	activation = c.fetchone()
	conn.close()
	return activation


def exists_activation(username):
	"""
	:param username: string
	:return: whether there is an activation for a user in the database
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	c.execute('SELECT * FROM activations WHERE user=?', (username,))
	activation = c.fetchone()
	conn.close()
	return activation is not None


def create_user(username, name, password):
	"""
	Creates a new user in the database with fields (username, name, salted password. salt)
	:param username: string
	:param name: string
	:param password: string
	"""
	print('Creating user', username, name, password)
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	salt = random.randint(0, 1000000)
	c.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (username, name, sha3(password + str(salt)), salt,))
	conn.commit()
	conn.close()
	remove_activation(username)


def update_password(username, password):
	"""
	Updates salt and salted password
	:param username: string
	:param password: string
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	salt = random.randint(0, 1000000)
	c.execute('UPDATE users SET password=?, salt=? WHERE username=?', (sha3(password + str(salt)), salt, username,))
	conn.commit()
	conn.close()
	remove_activation(username)


def remove_activation(username):
	"""
	Removes all activations by a username
	:param username: strinig
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	c.execute('DELETE FROM activations WHERE user=?', (username,))
	conn.commit()
	conn.close()


def add_activation(username):
	"""
	If activation from user exists, updates the time and code.
	Else makes a new activation with fields (username, code, timestamp)
	:param username: string
	:return code generated (sha3 of username + random int 0-1000
	"""
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	code = sha3(username + str(random.randint(0, 1000)))
	c.execute('SELECT * FROM activations WHERE user=?', (username,))
	if c.fetchone():
		c.execute('UPDATE activations SET code=?, timestamp=? WHERE user=?', (code, time.time(), username,))
	else:
		c.execute('INSERT INTO activations VALUES (NULL, ?, ?, ?)', (username, code, time.time(),))
	conn.commit()
	conn.close()
	return code


def send_activation_email(username, link):
	sg = sendgrid.SendGridAPIClient(apikey = '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')
	from_email = Email("buclasses@no-reply.com")
	to_email = Email('%s@bu.edu' % username)
	subject = "Setup email for BU Classes"
	email_content = Content("text/html", '<a href="%s">Click here</a> to set your password<br><br>OR<br><br>Copy this link in your browser:<br>%s' % (link, link))
	my_mail = Mail(from_email, subject, to_email, email_content)
	response = sg.client.mail.send.post(request_body = my_mail.get())
	print(response.status_code)
	print(response.body)
	print(response.headers)


def sha3(msg):
	s = hashlib.sha3_512()
	s.update(msg.encode())
	return s.hexdigest()


def insert_class(username, data):
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	
	classes = search_classes([data['semester'], data['college'], data['department'], data['course'], data['section']])
	for cls in classes:
		section = get(cls, 'Class')[4:]
		section = section[section.index(' ') + 1:]
		c.execute('SELECT * FROM classes WHERE user=? AND semester_code=? AND college=? AND department=? AND course=? And section=?', (username, data['semester'], data['college'], data['department'], data['course'], section,))
		if not c.fetchone():
			c.execute('INSERT INTO classes VALUES (NULL, ?, ?, ?, ?, ?, ?, 0)', (username, data['semester'], data['college'], data['department'], data['course'], section,))
	conn.commit()
	conn.close()


def delete_class(class_ids):
	conn = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	c = conn.cursor()
	for class_id in class_ids:
		c.execute('DELETE FROM classes WHERE id=?', (class_id,))
	conn.commit()
	conn.close()


if __name__ == "__main__":
	con = sqlite3.connect(path.join(ROOT, "sqldatabase.db"))
	cur = con.cursor()
	
	cur.execute('SELECT * FROM classes')
	records = cur.fetchall()
	
	# classes = []
	# for record in records:
	# 	if record[-1] == 1:
	# 		continue
	# 	searched = search_classes(record[2:-1])
	# 	for cls in searched:
	# 		cls.append(record[0])
	# 	classes += searched
	classes = [[['CAS CH203 B0'], ['Organic Chem 1', 'Loy'], [], ['0.0'], ['Discussion'], ['0'], ['BRB'], ['122'], ['Mon'], ['9:05am'], ['9:55am'], ['Class Full'], 32], [['CAS CS111 A2'], ['Int Comp Sci 1', 'Sullivan'], [], ['0.0'], ['Lab'], ['1'], ['CAS'], ['116'], ['Mon'], ['1:25pm'], ['2:15pm'], ['Class Full'], 33]]
	
	for i, cls in enumerate(classes):
		seats = get(cls, 'Seats')[0]
		if get(cls, 'Class') == 'Class':
			continue
		
		if seats == '0':
			log('No seats free in %s' % get(cls, 'Class'))
		else:
			log('********** %s Open **********' % get(cls, 'Class'))
			sg = sendgrid.SendGridAPIClient(apikey = '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')
			from_email = Email("buclasses@no-reply.com")
			to_email = Email('%s@bu.edu' % records[i][1])
			print('%s@bu.edu' % records[i][1])
			pass
			subject = 'Someone left %s!' % get(cls, 'Class')
			email_content = Content("text/html", '%s has now %s %s left<br><h5>Hurry up and join!</h5>' % (get(cls, 'Class'), seats, 'seat' if seats == '1' else 'seats'))
			my_mail = Mail(from_email, subject, to_email, email_content)
			response = sg.client.mail.send.post(request_body = my_mail.get())
			print(response.status_code)
			print(response.body)
			print(response.headers)
			cur.execute('UPDATE classes SET hold=1 WHERE user=?', (records[i][1],))
	cur.close()
