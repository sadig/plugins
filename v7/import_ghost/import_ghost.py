# -*- coding: utf-8 -*-

# Copyright © 2017 Stephan Ruegamer and others

# Permission is hereby granted, free of charge, to any
# person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the
# Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the
# Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice
# shall be included in all copies or substantial portions of
# the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
# OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
import os
import json
from dateutil import parser
import datetime

from nikola.plugin_categories import Command
from nikola import utils

from jinja2 import Environment, FileSystemLoader

LOGGER = utils.get_logger('import_ghost', utils.STDERR_HANDLER)


class CommandImportGhost(Command):
    """Import a ghost blog export."""

    name = "import_ghost"
    needs_config = False
    doc_usage = "[options] <filename>"
    doc_purpose = "import ghost blog export file"

    def _execute(self, options, args):
        """Import a Page."""
        if not args:
            print(self.help())
            return
        ghost_json_file = args[0]
        self._tmpl_env = Environment(loader=FileSystemLoader(
            '{0}/templates'.format(os.path.dirname(__file__))))
        self._post_directory = None
        for dir, where, template  in self.site.config['POSTS']:
            if dir.find('*.md') != -1:
                self._post_directory = dir.replace('/*.md', '')
        self._page_directory = None
        for dir, where, template in self.site.config['PAGES']:
            if dir.find('*.md') != -1:
                self._page_directory = dir.replace('/*.md', '')
        if self._post_directory is None or self._page_directory is None:
            print('You need to configure a markdown directory for '
                  'your pages and posts')
            return

        self._import_ghost_blog(ghost_json_file)

    def _import_ghost_blog(self, filename):
        if not os.path.exists(filename):
            print('ERROR: {0} does not exist!'.format(filename))
            return
        with open(filename, 'rb') as fp:
            ghost_content = json.load(fp)
            if 'db' in ghost_content:
                for db_entry in ghost_content['db']:
                    if 'data' in db_entry:
                        if 'posts' in db_entry['data'] \
                                and 'tags' in db_entry['data'] \
                                and 'posts_tags' in db_entry['data']:
                            self._write_documents_from_posts(
                                db_entry['data']['posts'],
                                db_entry['data']['tags'],
                                db_entry['data']['posts_tags'])
                            return
            return

    def _write_documents_from_posts(self, posts, tags,
                                    post_tags):
        # Convert tags:
        tags_dict = self._translate_tags(tags)
        new_posts = []
        for entry in posts:
            if entry['page'] == 0:
                if entry['status'] == 'published':
                    post = {}
                    post['title'] = entry['title']
                    post['slug'] = entry['slug']
                    post['markdown'] = entry['markdown']
                    post['author'] = 'sruegamer'
                    tag_ids = self._find_post_in_posttags(entry['id'],
                                                          post_tags)
                    post['tags'] = ','.join(
                        [tags_dict[tag]['name'] for tag in tag_ids])
                    post['published'] = parser.parse(entry['published_at'])
                    new_posts.append(post)
                if entry['status'] == 'draft':
                    post = {}
                    post['title'] = entry['title']
                    post['slug'] = entry['slug']
                    post['markdown'] = entry['markdown']
                    post['author'] = 'sruegamer'
                    tag_ids = self._find_post_in_posttags(entry['id'],
                                                          post_tags)
                    post['tags'] = ','.join(
                        [tags_dict[tag]['name'] for tag in tag_ids])
                    if len(post['tags']) > 0:
                        post['tags'] = post['tags'] + ',draft'
                    else:
                        post['tags'] = 'draft'
                    post['published'] = parser.parse(entry['created_at'])
                    new_posts.append(post)
                self._write_posts(new_posts)
        print('Imported {0} posts'.format(len(new_posts)))
        return

    def _write_posts(self, posts):
        template = self._tmpl_env.get_template('nikola_document.tmpl')
        for post in posts:
            if not os.path.exists(
                    '{0}/{1}/{2}/{3}'.format(self._post_directory,
                                             post['published'].year,
                                             post['published'].month,
                                             post['published'].day)):
                os.makedirs(
                    '{0}/{1}/{2}/{3}'.format(self._post_directory,
                                             post['published'].year,
                                             post['published'].month,
                                             post['published'].day))

            with open('{0}/{1}/{2}/{3}/{4}.md'.format(
                self._post_directory,
                post['published'].year, post['published'].month,
                post['published'].day, post['slug']), 'wb') as fp:
                fp.write(template.render({'post': post}).encode('utf-8'))

    def _find_post_in_posttags(self, post_id, post_tags):
        tag_ids = []
        for i in post_tags:
            if i['post_id'] == post_id:
                if i['tag_id'] not in tag_ids:
                    tag_ids.append(i['tag_id'])
        return tag_ids

    def _translate_tags(self, tags):
        tag_dict = {}
        for tag in tags:
            if tag['id'] not in tag_dict:
                tag_dict[tag['id']] = {}
            tag_dict[tag['id']] = {
                'name': tag['name'],
                'slug': tag['slug']
            }
        return tag_dict
