import unicodedata

from bs4 import BeautifulSoup
import requests


main_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/uismpl/1204835367?ModuleName=univschs.pl"
search_url = "https://www.bu.edu/link/bin/uiscgi_studentlink.pl/1510675812?ModuleName=univschr.pl&SearchOptionDesc=Class+Number&SearchOptionCd=S&KeySem=%s&ViewSem=%s&College=%s&Dept=%s&Course=%s&Section=%s&MainCampusInd=%s"


indexes = {'Class': 0, 'Title': 1, 'Credits': 3, 'Type': 4, 'Seats': 5, 'Building': 6, 'Room': 7, 'Day': 8, 'Start': 9, 'Stop': 10, 'Notes': 11}


def get(record, index, i):
    if index == indexes['Class'] and i == 0:
        return ' '.join(record[index])
    if i < len(record[index]) and index != 0:
        return record[index][i]
    return ''


def search_classes(verbose):
    soup = BeautifulSoup(requests.get(main_url).text, "html.parser")
    
    # Get semester
    sem_list = str(soup.find('select', attrs={'name':'SemList'})).split('<option ')[2:]
    sem_list = [x[:x.index('\n') if '\n' in x else len(x)] for x in sem_list]
    sem_values = []
    for sem in sem_list:
        sem_values.append([sem[sem.index('"') + 1:sem.rindex('"')] , sem[sem.index('>') + 1:]])
         
    print('Semester:')
    for i, v in enumerate(sem_values):
        print('%d. %s' % (i + 1, v[1]))
         
        try:
            sem_index = int(input('Enter the number of the semester: '))
            if sem_index < 1 or sem_index > len(sem_values):
                raise IndexError
            break
        except ValueError:
            print('Not a number')
        except IndexError:
            print('Number out of range')
     
     
    # # Get class
    college = input('College (eg. CAS): ').upper()
    dept = input('Department (eg. CS or PH): ').upper()
    course = input('Course (eg. 101): ')
    
    # sem_values = [['20184', 'Spring 2018']]
    # sem_index = 1
    # college = 'CAS'
    # dept = 'PH'
    # course = '360'
    section = ''
    crco = 'N'
    
    # # Search
    data = []
    while True:
        info = []
        custom_url = search_url % (sem_values[sem_index - 1][0], sem_values[sem_index - 1][1], college, dept, course, section, crco)
        r = requests.get(custom_url)
        soup = BeautifulSoup(str(r.text), "html.parser")
        soup = BeautifulSoup(str(soup.find_all('table')[5]), "html.parser")
        for i, tr in enumerate(soup.find_all('tr')):
            record = []
            for j, td in enumerate(tr.find_all(['td', 'th'])):
                if j == 0:
                    continue
                td = str(td.get_text(separator=';', strip=True))
                td = unicodedata.normalize("NFKD", td)
                if j == 1:
                    td = td.split(' ')
                else:
                    td = td.split(';')
                    td = [item for item in td if str(item)]
                record.append(td)
            if len(record) != 12:
                continue
            data.append(record)
        done = True
        for record in data:
            cls = record[indexes['Class']]
            if len(cls) < 3:
                info.append(record)
                continue
            if cls[1] != dept + course:
                done = True
            else:
                done = False
                if not verbose:
                    if record[indexes['Seats']][0] != '0':
                        info.append(record)
                else:
                    info.append(record)
                section = cls[2]
        if done:
            break
        
    for record in info:
        # get biggest length in record
        max_len = 0
        for i, field in enumerate(record):
            if i == 0:
                continue
            if len(field) > max_len:
                max_len = len(field)
        
        # pretty print
        for i in range(max_len):
            print('%12s  %15s  %3s  %22s  %5s  %3s  %4s  %15s  %7s  %7s  %15s' % (
            get(record, indexes['Class'], i), get(record, indexes['Title'], i), get(record, indexes['Credits'], i), get(record, indexes['Type'], i), get(record, indexes['Seats'], i), get(record, indexes['Building'], i), get(record, indexes['Room'], i), get(record, indexes['Day'], i), get(record, indexes['Start'], i), get(record, indexes['Stop'], i), get(record, indexes['Notes'], i)
            ))


def display_menu():
    print('1. Search classes')
    print('2. Show only available classes')
    print('3. Show all classes')
    print('4. Read from file')
    print('0. Quit\n')
 
 
def menu():
    verbose = True
    while (True):
        display_menu()
        choice = input('Enter your choice: ')
        if choice == '1':
            search_classes(verbose)
        elif choice == '2':
            verbose = False
        elif choice == '3':
            verbose = True
        elif choice == '0':
            break
        else:
            print('\nInvalid Choice')
        print()
