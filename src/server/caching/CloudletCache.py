#!/usr/bin/env python
#
# Elijah: Cloudlet Infrastructure for Mobile Computing
# Copyright (C) 2011-2012 Carnegie Mellon University
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of version 2 of the GNU General Public License as published
# by the Free Software Foundation.  A copy of the GNU General Public License
# should have been distributed along with this program in the file
# LICENSE.GPL.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#

import os
import sys
import threading 
import requests
from BeautifulSoup import BeautifulSoup
from Queue import Queue, Empty


# URL fetching thread
# python has multitheading issue
FETCHING_THREAD_NUM = 2


class CachingError(Exception):
    pass


class _URIInfo(object):
    URI             = "uri"
    NAME            = "name"
    SIZE            = "size"
    LAST_MODIFIED   = "last_modified"

    def __init__(self, uri, name, size, last_modified):
        self.info_dict = {
                _URIInfo.URI : uri,
                _URIInfo.NAME : name,
                _URIInfo.SIZE : size,
                _URIInfo.LAST_MODIFIED : last_modified,
                }
    def __repr__(self):
        import pprint
        return pprint.pformat(self.info_dict)


class _URIParser(threading.Thread):
    CHARSET = "utf-8"

    def __init__(self, visited_set, uri_queue, cache_dir=None, print_out=None):
        self.visited_set = visited_set
        self.uri_queue = uri_queue
        self.compiled_list = list()
        self.cache_dir = cache_dir
        self.print_out = print_out
        if self.print_out == None:
            self.print_out = open("/dev/null", "w+b")
        self.stop = threading.Event()

        threading.Thread.__init__(self, target=self.parse)

    def _is_file(self, header):
        content_type = header.get('content-type', None)
        if content_type == None:
            return True
        if content_type.find('html') != -1:
            return False
        return True

    def parse(self):
        is_first_time_access = True
        while(not self.stop.wait(0.0001)):
            try:
                if is_first_time_access:
                    url = self.uri_queue.get(True, 1) # block for 1 second
                    is_first_time_access = True
                else:
                    url = self.uri_queue.get_nowait()
                header_ret = requests.head(url)
                if header_ret.ok == True:
                    header = header_ret.headers
                else:
                    continue
            except Empty:
                break
            except UnicodeDecodeError:
                continue

            cache_filepath = None
            if self.cache_dir != None:
                parse_ret = requests.utils.urlparse(url)
                url_path = parse_ret.path[1:] # remove "/"
                cache_filepath = os.path.join(self.cache_dir, parse_ret.netloc, url_path)
                # save to disk
                if self._is_file(header) == True:
                    dirpath = os.path.dirname(cache_filepath)
                    if os.path.exists(dirpath) == False:
                        os.makedirs(dirpath)
                    r = requests.get(url, stream=True)
                    if r.ok: 
                        diskfile = open(cache_filepath, "w+b")
                        self.print_out.write("%s --> %s\n" % (url, cache_filepath))
                        while True:
                            raw_data = r.raw.read(1024*1024*5)
                            if raw_data == None or len(raw_data) == 0:
                                break
                            diskfile.write(raw_data)
                        diskfile.close()
                else:
                    if os.path.exists(cache_filepath) == False:
                        os.makedirs(cache_filepath)

            self.compiled_list.append(_URIInfo(url, cache_filepath, \
                    header.get('content-length', None),
                    header.get('last-modified', None)))
            if self._is_file(header) == True:
                # leaf node
                pass
            else:
                try:
                    r = requests.get(url)
                except UnicodeDecodeError:
                    continue
                for link in BeautifulSoup(r.text).findAll('a'):
                    try:
                        href = link['href']
                    except KeyError:
                        continue
                    if not href.startswith('http://'):
                        if href[0] == '/':
                            href = href[1:]
                        parse_ret = requests.utils.urlparse('%s%s' % (r.url, href))
                        new_uri = "%s://%s%s" % (parse_ret.scheme, parse_ret.netloc, parse_ret.path)
                    else:
                        new_uri = href

                    if new_uri not in self.visited_set:
                        self.visited_set.add(new_uri)
                        self.uri_queue.put(new_uri)

    def terminate(self):
        self.stop.set()


class CacheUtil(object):
    @staticmethod
    def is_valid_uri(uri, is_source_uri=False):
        parse_ret = requests.utils.urlparse(uri)
        if len(parse_ret.scheme) == 0:
            return False
        if len(parse_ret.scheme) == 0:
            return False
        if len(parse_ret.netloc) == 0:
            return False
        if not is_source_uri:
            if len(parse_ret.query) > 0:
                return False
        return True

    @staticmethod
    def get_compiled_URIs(sourceURI):
        if not CacheUtil.is_valid_uri(sourceURI, is_source_uri=True):
            msg = "Invalid URI: %s" % sourceURI
            raise CachingError(msg)
        visited = set()
        uri_queue = Queue()
        uri_queue.put(host)
        thread_list = []
        for index in xrange(FETCHING_THREAD_NUM):
            parser = _URIParser(visited, uri_queue)
            thread_list.append(parser)
            parser.start()

        compiled_list = list()
        try:
            while len(thread_list) > 0:
                t = thread_list[0]
                t.join(timeout=1.0)
                if not t.is_alive():
                    compiled_list.extend(t.compiled_list) 
                    thread_list.remove(t)
        except KeyboardInterrupt, e:
            for t in thread_list:
                t.terminate()
                t.join()
            sys.stderr.write("Keyboard Interrupt")
        return compiled_list

    @staticmethod
    def get_cache_score(compiledURI_list):
        cache_score = 0
        return cache_score


class CacheManager(threading.Thread):
    def __init__(self, cache_dir, print_out=None):
        self.cache_dir = cache_dir
        self.print_out = print_out
        if self.print_out == None:
            self.print_out = open("/dev/null", "w+b")

    def fetch_source_URI(self, sourceURI):
        if not CacheUtil.is_valid_uri(sourceURI, is_source_uri=True):
            raise CachingError("Invalid URI: %s" % sourceURI)
        visited = set()
        uri_queue = Queue()
        uri_queue.put(host)
        thread_list = []
        for index in xrange(3):
            parser = _URIParser(visited, uri_queue, cache_dir=self.cache_dir,
                    print_out=self.print_out)
            thread_list.append(parser)
            parser.start()

        compiled_list = list()
        for t in thread_list:
            t.join()
            compiled_list.extend(t.compiled_list) 
        return compiled_list


    def fetch_compiled_URIs(self, URIInfo_list):
        """ Warm cache from the URI list
        Exception:
            CachingError if failed to fetching URI
        """
        for each_info in URIInfo_list:
            compiled_uri = each_info.info_dict[_URIInfo.URI]
            if not CacheUtil.is_valid_uri(compiled_uri):
                raise CachingError("Invalid URI: %s" % compiled_uri)

        for each_info in URIInfo_list:
            uri = each_info.info_dict[_URIInfo.URI]
            parse_ret = requests.utils.urlparse(uri)
            uri_path = parse_ret.path[1:] # remove "/"
            diskpath = os.path.join(self.cache_dir, parse_ret.netloc, uri_path)
            # save to disk
            if diskpath.endswith('/') == False and os.path.isdir(diskpath) == False:
                dirpath = os.path.dirname(diskpath)
                if os.path.exists(dirpath) == False:
                    os.makedirs(dirpath)
                r = requests.get(uri, stream=True)
                if r.ok: 
                    diskfile = open(diskpath, "w+b")
                    self.print_out.write("%s --> %s\n" % (uri, diskpath))
                    while True:
                        raw_data = r.raw.read(1024*1024*5)
                        if raw_data == None or len(raw_data) == 0:
                            break
                        diskfile.write(raw_data)
                    diskfile.close()
            else: # directory
                if os.path.exists(diskpath) == False:
                    os.makedirs(diskpath)

    def launch_fuse(self, URI_list, samba_dir):
        """ Construct FUSE directory structure at give Samba directory
        Return:
            fuse obejct that has connection to FUSE executable 
        """
        fuse = None
        return fuse


# Global
cache_rootdir = '/tmp/cloudlet_cache/'
cache_manager = CacheManager(cache_rootdir, print_out=sys.stdout)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "> $ prog [root_uri]"
        sys.exit(1)

    host = sys.argv[1]
    compiled_list = CacheUtil.get_compiled_URIs(host)
    try:
        cache_manager.fetch_compiled_URIs(compiled_list)
    except CachingError, e:
        print str(e)
