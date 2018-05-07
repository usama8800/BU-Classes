import hashlib
import random
import smtplib
import sqlite3
import time
import unicodedata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

main_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/uismpl/1204835367?ModuleName=univschs.pl"
search_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/1510675812?ModuleName=univschr.pl&SearchOptionDesc=Class+Number&SearchOptionCd=S&KeySem=%s&ViewSem=%s&College=%s&Dept=%s&Course=%s&Section=%s&MainCampusInd=%s"
indexes = {'Class': 0, 'Title': 1, 'Credits': 3, 'Type': 4, 'Seats': 5, 'Building': 6, 'Room': 7, 'Day': 8, 'Start': 9, 'Stop': 10, 'Notes': 11}


def get(record, index, i=-1):
	if i == -1:
		if len(record[indexes[index]]) == 1:
			return record[indexes[index]][0]
		return record[indexes[index]]
	if i < len(record[indexes[index]]):
		return record[indexes[index]][i]
	return ''


def search_classes(class_info, verbose=True):
	section = class_info[5]
	crco = 'N'
	data = []
	while True:
		info = []
		custom_url = search_url % (class_info[0], class_info[1], class_info[2], class_info[3], class_info[4], section, crco)  # Create the custom URL with the user values
		soup = BeautifulSoup(str(requests.get(custom_url).text), "html.parser")  # Get the text from the URL and parse it
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
			if (class_info[3] not in cls or class_info[4] not in cls or (class_info[5] != '' and class_info[5] not in cls[-2:])) and cls != 'Class':
				done = True
			else:
				done = False
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
	user = get_user(username)
	if not user:
		return {'error': {'user': 'User not found'}}
	if not check_password(user, password):
		return {'error': {'pass': 'Invalid password'}}
	
	conn = sqlite3.connect('sqldatabase.db')
	c = conn.cursor()
	c.execute('SELECT * FROM classes WHERE user=?', (user[0],))
	records = [record[2:9] for record in c.fetchall()]
	conn.close()
	classes = []
	for record in records:
		if record[-1] == 1:
			continue
		classes += search_classes(record)
	return {'classes': classes, 'name': user[1], 'error': False}


def check_password(user, password):
	return user[2] == sha3(password + str(user[3]))


def get_user(username):
	conn = sqlite3.connect('sqldatabase.db')
	c = conn.cursor()
	c.execute('SELECT * FROM users WHERE username=?', (username,))
	user = c.fetchone()
	conn.close()
	return user


def get_activation(code):
	conn = sqlite3.connect('sqldatabase.db')
	c = conn.cursor()
	c.execute('SELECT * FROM activations WHERE code=?', (code,))
	activation = c.fetchone()
	conn.close()
	return activation


def exists_activation(username):
	conn = sqlite3.connect('sqldatabase.db')
	c = conn.cursor()
	c.execute('SELECT * FROM activations WHERE user=?', (username,))
	activation = c.fetchone()
	conn.close()
	return activation is not None


def create_user(username, name, password):
	print('Creating user', username, name, password)
	conn = sqlite3.connect('sqldatabase.db')
	c = conn.cursor()
	salt = random.randint(0, 1000000)
	c.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (username, name, sha3(password + str(salt)), salt,))
	conn.commit()
	conn.close()
	remove_activation(username)


def update_password(username, password):
	conn = sqlite3.connect('sqldatabase.db')
	c = conn.cursor()
	salt = random.randint(0, 1000000)
	c.execute('UPDATE users SET password=?, salt=? WHERE username=?', (sha3(password + str(salt)), salt, username,))
	conn.commit()
	conn.close()
	remove_activation(username)


def remove_activation(username):
	conn = sqlite3.connect('sqldatabase.db')
	c = conn.cursor()
	c.execute('DELETE FROM activations WHERE user=?', (username,))
	conn.commit()
	conn.close()


def add_activation(username):
	conn = sqlite3.connect('sqldatabase.db')
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
	fromaddr = "usama8800@gmail.com"
	toaddr = '%s@bu.edu' % username
	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(fromaddr, "nqfkaexanhjlbwcw")
	msg = MIMEMultipart()
	msg['From'] = ''
	msg['To'] = toaddr
	msg['Subject'] = 'Setup email for BU Classes'
	body = '<a href="%s">Click here</a> to set your password<br><br>OR<br><br>Copy this link in your browser:<br>%s' % (link, link)
	msg.attach(MIMEText(body, 'html'))
	server.sendmail(fromaddr, fromaddr, msg.as_string())


def sha3(msg):
	s = hashlib.sha3_512()
	s.update(msg.encode())
	return s.hexdigest()


if __name__ == "__main__":
	x = get_classes('usama', 'Pp[]1qse4')
