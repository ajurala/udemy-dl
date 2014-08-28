#!/usr/bin/env python
# -*- coding: utf8 -*-

import requests
import argparse
import getpass
import sys
import re
import os
import json
from bs4 import BeautifulSoup
import urllib2

class Session:
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:18.0) Gecko/20100101 Firefox/18.0',
               'X-Requested-With': 'XMLHttpRequest',
               'Referer': '	http://www.udemy.com/'}

    def __init__(self):
        self.session = requests.Session()
#!/usr/bin/env python
# -*- coding: utf8 -*-

import requests
import argparse
import getpass
import sys
import re
import os
import json
from bs4 import BeautifulSoup
import urllib2


class Session:
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:18.0) Gecko/20100101 Firefox/18.0',
               'X-Requested-With': 'XMLHttpRequest',
               'Referer': ' http://www.udemy.com/'}

    def __init__(self):
        self.session = requests.Session()

    def get(self, url):
        return self.session.get(url, headers=self.headers)

    def post(self, url, data):
        return self.session.post(url, data, headers=self.headers)


session = Session()


def get_csrf_token():
    response = session.get('https://www.udemy.com/join/login-popup')
    soup = BeautifulSoup(response.text)
    return soup.find_all('input', {'name': 'csrf'})[0]['value']


def login(username, password):
    login_url = 'https://www.udemy.com/join/login-submit'
    csrf_token = get_csrf_token()
    payload = {'isSubmitted': 1, 'email': username, 'password': password,
               'displayType': 'json', 'csrf': csrf_token}
    response = session.post(login_url, payload).json()
    if 'error' in response:
        print(response['error']['message'])
        sys.exit(1)


def get_course_id(course_link):
    response = session.get(course_link)
    matches = re.search('data-courseId="(\d+)"', response.text)
    return matches.groups()[0]


def parse_video_url(lecture_id):
    '''A hacky way to find the json used to initalize the swf object player'''
    embed_url = 'https://www.udemy.com/embed/{0}'.format(lecture_id)
    html = session.get(embed_url).text

    data = re.search(r'\$\("#player"\).jwplayer\((.*?)\);.*</script>', html,
                     re.MULTILINE | re.DOTALL).group(1)
    video = json.loads(data)

    if 'playlist' in video and 'sources' in video['playlist'][0]:
        source = video['playlist'][0]['sources'][0]
        return source['file']
    else:
        return None


def get_video_links(course_id):
    course_url = 'https://www.udemy.com/api-1.1/courses/{0}/curriculum?fields[lecture]=@min,completionRatio,progressStatus&fields[quiz]=@min,completionRatio'.format(course_id)
    course_data = session.get(course_url).json()

    chapter = None
    video_list = []

    lecture_number = 0
    chapter_number = 0
    # A udemy course has chapters, each having one or more lectures
    for item in course_data:
        if item['__class'] == 'chapter':
            chapter = item['title']
            chapter_number += 1
            lecture_number = 1
        elif item['__class'] == 'lecture' and item['assetType'] == 'Video':
            lecture = item['title']
            try:
                lecture_id = item['id']
                video_url = parse_video_url(lecture_id)
                video_list.append({'chapter': chapter,
                                   'lecture': lecture,
                                   'video_url': video_url,
                                   'lecture_number': lecture_number,
                                   'chapter_number': chapter_number})
            except:
                print('Cannot download lecture "%s"' % (lecture))
            lecture_number += 1
    return video_list


def sanitize_path(s):
    return "".join([c for c in s if c.isalpha() or c.isdigit() or c in ' .-_,']).rstrip()


def mkdir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def dl_progress(bytes_so_far, total_size):
    progress = bytes_so_far * 100 / total_size
    if bytes_so_far != 0:
        sys.stdout.write(4 * '\b')
    sys.stdout.write('%3d%%' % (progress))


def down_url(link, filename,proxy=None):
    opener = None
    if proxy is not None:
        proxy = urllib2.ProxyHandler({'http': proxy})
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
    else:
        opener = urllib2.build_opener();

    response = opener.open(link)
    filesize = float(response.info()['Content-Length'])

    count = 0
    bytes_so_far = 0
    chunk_size = 8192
    chunk = None

    if (os.path.exists(filename) and os.path.isfile(filename)):
        count = os.path.getsize(filename)

#    print "Current File Size: " + str(count)
#    print "Network File Size: " + str(filesize)
    response.close()
    if count >= filesize:
        return

    req = urllib2.Request(link)
    req.add_header("Range","bytes=%s-" % (count))
    response = opener.open(req)
    outfile = open(filename,"ab")

    dl_progress(bytes_so_far, filesize)
    while 1:
        try:
            chunk = self.response.read(chunk_size)
        except:
            chunk = None

        if not chunk:
            break

        bytes_so_far += len(chunk)
        outfile.write(chunk)
        dl_progress(bytes_so_far, filesize)

def get_video(directory, filename, link, proxy):
    print('Downloading %s  ' % (filename)),
    mkdir(directory)
    os.chdir(directory)
    #if not os.path.exists(filename):
    down_url(link, filename, proxy)
    os.chdir('..')
    print()


def udemy_dl(username, password, course_link):
    login(username, password)

    course_id = get_course_id(course_link)

    for video in get_video_links(course_id):
        directory = '%02d %s' % (video['chapter_number'], video['chapter'])
        filename = '%03d %s.mp4' % (video['lecture_number'], video['lecture'])

        directory = sanitize_path(directory)
        filename = sanitize_path(filename)

        get_video(directory, filename, video['video_url'], None)

    session.get('http://www.udemy.com/user/logout')


def main():
    parser = argparse.ArgumentParser(description='Fetch all the videos for a udemy course')
    parser.add_argument('link', help='Link for udemy course', action='store')
    parser.add_argument('-u', '--username', help='Username/Email', default=None, action='store')
    parser.add_argument('-p', '--password', help='Password', default=None, action='store')

    args = vars(parser.parse_args())

    username = args['username']
    password = args['password']
    link = args['link']

    if not username:
        print('Username/Email:'),
        username = raw_input()
    if not password:
        password = getpass.getpass(prompt='Password: ')

    udemy_dl(username, password, link)

if __name__ == '__main__':
    main()