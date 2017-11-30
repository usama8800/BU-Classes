import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import socket
import sys
import time
import unicodedata

from bs4 import BeautifulSoup
import requests


main_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/uismpl/1204835367?ModuleName=univschs.pl"
search_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/1510675812?ModuleName=univschr.pl&SearchOptionDesc=Class+Number&SearchOptionCd=S&KeySem=%s&ViewSem=%s&College=%s&Dept=%s&Course=%s&Section=%s&MainCampusInd=%s"
indexes = {'Class': 0, 'Title': 1, 'Credits': 3, 'Type': 4, 'Seats': 5, 'Building': 6, 'Room': 7, 'Day': 8, 'Start': 9, 'Stop': 10, 'Notes': 11}

def log(arg=''):
    print(arg)
    file = open('log.txt', 'a')
    file.write(arg + '\n')
    file.close()    

def get(record, index, i=-1):
    if i == -1:
        if len(record[indexes[index]]) == 1:
            return record[indexes[index]][0]
        return record[indexes[index]]
    if i < len(record[indexes[index]]):
        return record[indexes[index]][i]
    return ''

def search_classes(class_info, verbose=True):
    section = class_info[4]
    crco = 'N'
    data = []
    while True:
        info = []
        custom_url = search_url % (class_info[0][0], class_info[0][1], class_info[1], class_info[2], class_info[3], section, crco)  # Create the custom URL with the user values
        soup = BeautifulSoup(str(requests.get(custom_url).text), "html.parser")  # Get the text from the URL and parse it
        soup = BeautifulSoup(str(soup.find_all('table')[5]), "html.parser")  # Parse the 6th table which contains the class list
        for i, tr in enumerate(soup.find_all('tr')):
            record = []
            for j, td in enumerate(tr.find_all(['td', 'th'])):
                if j == 0:  # First item is always empty
                    continue
                td = str(td.get_text(separator=';', strip=True))  # gets the text with ; in between if there is more than one line
                td = unicodedata.normalize("NFKD", td)  # Convert the unicode characters to utf-8
                td = td.split(';')  # Split the td into lines
                td = [item for item in td if str(item)]  # Get rid of empty strings
                record.append(td)  # Add field to record
            if len(record) == 12 and (i != 0 or section == ''):  # Don't add the rows which are not classes and don't add the header row for second page
                data.append(record) 
        # Checks if we need to go to the next page for more classes and filter the classes
        done = True
        for record in data:
            cls = get(record, 'Class')  # Get the class - CAS CS112 A1
            if (class_info[2] not in cls or class_info[3] not in cls or (class_info[4] != '' and class_info[4] not in cls[-2:])) and cls != 'Class':
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

def print_classes(classes):
    for cls in classes:
        # get biggest length in cls
        max_len = 0
        for i, field in enumerate(cls):
            if i == 0:
                continue
            if len(field) > max_len:
                max_len = len(field)
        
        # pretty print
        for i in range(max_len):
            print('%12s  %15s  %3s  %22s  %5s  %3s  %4s  %15s  %7s  %7s  %15s' % (
                get(cls, 'Class', i), get(cls, 'Title', i), get(cls, 'Credits', i), get(cls, 'Type', i), get(cls, 'Seats', i), get(cls, 'Building', i), get(cls, 'Room', i), get(cls, 'Day', i), get(cls, 'Start', i), get(cls, 'Stop', i), get(cls, 'Notes', i)
            ))

def read_file():
    try:
        file = open('classes.txt', 'r')
    except FileNotFoundError:
        return
    for line in file.readlines():
        line = line[:-1]
        fields = line.split(';')
        classes = search_classes([[fields[0], fields[1]], fields[2], fields[3], fields[4], fields[5]])
        print_classes(classes)
    file.close()

def save_file(soup):
    file = open('classes.txt', 'a')
    data = get_user_input(soup)
    email = input('Enter your email: ')
    line = '%s;%s;%s;%s;%s;%s;%s\n' % (data[0][0], data[0][1], data[1], data[2], data[3], data[4], email)
    file.write(line)
    file.close()
    
def delete_entrys(lst):
    file = open('classes.txt', 'r')
    lines = file.readlines()
    for v in lst:
        del lines[v]
    file.close()
    file = open('classes.txt', 'w')
    file.writelines(lines)

def get_user_input(soup):
    sem_list = str(soup.find('select', attrs={'name':'SemList'})).split('<option ')[2:]
    sem_list = [x[:x.index('\n') if '\n' in x else len(x)] for x in sem_list]
    sem_values = []
    for sem in sem_list:
        sem_values.append([sem[sem.index('"') + 1:sem.rindex('"')] , sem[sem.index('>') + 1:]])
    if len(sem_list) == 0:
        raise BaseException('No Semester available')
    print('Semester:')
    for i, v in enumerate(sem_values):
        print('%d. %s' % (i + 1, v[1]))
        
    while True:
        sem_index = input('Semester (integer): ')
        if not sem_index.isdecimal():
            continue
        sem_index = int(sem_index) - 1
        if sem_index < 0 or sem_index >= len(sem_values):
            continue
        break
    while True:
        college = input('College (eg. CAS): ').upper()
        if college.isalpha() and len(college) == 3:
            break
    while True:
        dept = input('Department (eg. CS or PH): ').upper()
        if dept.isalpha() and len(dept) == 2:
            break
    while True:
        course = input('Course (eg. 101): ')
        if course.isdigit() and len(course) == 3:
            break
    section = input('Section (optional): ').upper()
    return [sem_values[sem_index], college, dept, course, section]
    
def manual_search(soup, verbose):
    classes = search_classes(get_user_input(soup), verbose)
    print_classes(classes)

def display_menu():
    print('1. Search classes')
    print('2. Show only available classes')
    print('3. Show all classes')
    print('4. Read from file')
    print('5. Save to file')
    print('0. Quit\n')

def menu():
    verbose = True
    main_soup = BeautifulSoup(requests.get(main_url).text, "html.parser")
    while (True):
        display_menu()
        choice = input('Enter your choice: ')
        if choice == '1':
            manual_search(main_soup, verbose)
        elif choice == '2':
            verbose = False
        elif choice == '3':
            verbose = True
        elif choice == '4':
            read_file()
        elif choice == '5':
            save_file(main_soup)
        elif choice == '0':
            break
        elif choice in ['run', 'main']:
            main()
        else:
            print('\nInvalid Choice')
        print()

def main():
    log('%s\nRunning on %s\n%s' % ('-' * 30, datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'), '-' * 30))
    file = open('classes.txt', 'r')
    dels = []
    
    fromaddr = "usama8800@gmail.com"
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(fromaddr, "nqfkaexanhjlbwcw")
    for i, line in enumerate(file.readlines()):
        fields = line[:-1].split(';')
        classes = search_classes([[fields[0], fields[1]], fields[2], fields[3], fields[4], fields[5]])
        toaddr = fields[6]
        for cls in classes:
            seats = get(cls, 'Seats')[0]
            if get(cls, 'Class') == 'Class':
                continue
            log('Searching %s' % get(cls, 'Class'))
            if seats != '0':
                msg = MIMEMultipart()
                msg['From'] = fromaddr
                msg['To'] = toaddr
                msg['Subject'] = 'Someone left %s!' % get(cls, 'Class')
                body = '%s has now %s %s left<br><h5>Hurry up and join!</h5>' % (get(cls, 'Class'), seats, 'seat' if seats == '1' else 'seats')
                msg.attach(MIMEText(body, 'html'))
                if toaddr != '':
                    server.sendmail(fromaddr, toaddr, msg.as_string())
                msg = MIMEMultipart()
                msg['From'] = fromaddr
                msg['To'] = fromaddr
                msg['Subject'] = 'Someone left %s!' % get(cls, 'Class')
                body = 'Email sent to %s' % toaddr
                msg.attach(MIMEText(body, 'html'))
                server.sendmail(fromaddr, fromaddr, msg.as_string())
                log('********** %s Open **********' % get(cls, 'Class'))
                
                dels.append(i)
                break
    delete_entrys(dels)

try:
    if __name__ == '__main__':
        if 'run' in sys.argv or 'main' in sys.argv:
            main()
        else:
            menu()
    else:
        main()
except (requests.ConnectionError, socket.gaierror) as e:
    log('Connectivity problem')
except Exception as e:
    log("Unexpected error: %s" % sys.exc_info()[0])
    print(e)

