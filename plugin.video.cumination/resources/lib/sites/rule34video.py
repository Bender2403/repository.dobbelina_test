"""
    Cumination
    Copyright (C) 2023 Team Cumination

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import re
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor
from resources.lib import utils
from resources.lib.adultsite import AdultSite
from six.moves import urllib_parse, urllib_request
from resources.lib.basics import profileDir

site = AdultSite('rule34video', '[COLOR hotpink]Rule34 Video[/COLOR]', 'https://rule34video.com/', 'rule34video.png', 'rule34video')


@site.register(default_mode=True)
def Main():
    site.add_dir('[COLOR hotpink]Categories[/COLOR]', site.url + 'categories/', 'Cats', site.img_cat)
    site.add_dir('[COLOR hotpink]Tags[/COLOR]', site.url + 'tags/', 'TagMenu', site.img_tags)
    site.add_dir('[COLOR hotpink]Search[/COLOR]', site.url + 'search/', 'Search', site.img_search)
    List(site.url + 'latest-updates/')
    utils.eod()


THUMB_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
THUMB_DIR = os.path.join(profileDir, 'thumbnails', 'rule34video')


def _thumb_ext(data):
    """Erkennt das echte Bildformat am Dateianfang."""
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if data[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    return None


def _fix_thumb(img):
    """Die Seite liefert WebP-Bilder mit .jpg-Endung, die Kodi 21.3 nicht anzeigt.
    Bild laden, echtes Format erkennen und mit passender Endung lokal speichern."""
    if not img:
        return img
    try:
        key = hashlib.md5(img.encode('utf-8')).hexdigest()
        for ext in ('webp', 'jpg', 'png'):
            cached = os.path.join(THUMB_DIR, '{0}.{1}'.format(key, ext))
            if os.path.exists(cached):
                return cached
        candidates = [img]
        for a, b in (('320x180', '336x189'), ('336x189', '320x180')):
            if a in img:
                candidates.append(img.replace(a, b))
        for url in candidates:
            try:
                req = urllib_request.Request(url, headers={'User-Agent': THUMB_UA, 'Referer': site.url})
                data = urllib_request.urlopen(req, timeout=15).read()
            except Exception:
                continue
            ext = _thumb_ext(data)
            if ext:
                os.makedirs(THUMB_DIR, exist_ok=True)
                path = os.path.join(THUMB_DIR, '{0}.{1}'.format(key, ext))
                with open(path, 'wb') as f:
                    f.write(data)
                return path
    except Exception as e:
        utils.kodilog('rule34video thumbnail: {0}'.format(e))
    return img


@site.register()
def List(url):
    listhtml = utils.getHtml(url, site.url)
    match = re.compile(r'open-popup"\s+href="([^"]+)".*?<img[^>]+src="([^"]+)"[^>]+alt="([^"]+)".*?(<div class="quality">.*?</div>)?.*?class="time">([^<]+)<', re.DOTALL | re.IGNORECASE).findall(listhtml)

    os.makedirs(THUMB_DIR, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as executor:
        fixed_imgs = list(executor.map(_fix_thumb, [m[1] for m in match]))

    for (videopage, _img, name, hd, duration), img in zip(match, fixed_imgs):
        name = utils.cleantext(name.strip())
        hd = " [COLOR orange]HD[/COLOR]" if 'hd' in hd else ''

        cm = []
        cm_lookupinfo = (utils.addon_sys + "?mode=" + str('rule34video.Lookupinfo') + "&url=" + urllib_parse.quote_plus(videopage))
        cm.append(('[COLOR deeppink]Lookup info[/COLOR]', 'RunPlugin(' + cm_lookupinfo + ')'))

        site.add_download_link(name, videopage, 'Playvid', img, name, duration=duration, quality=hd, contextm=cm)

    nextp = re.compile(r'pager\s*next">.+?block-id="([^"]+)"\s*data-parameters="([^"]+)', re.DOTALL | re.IGNORECASE).findall(listhtml)

    if nextp:
        currpg = re.compile(r'class="pagination".+?class="item\sactive">.+?from(?:_albums)?:(\d+)', re.DOTALL | re.IGNORECASE).findall(listhtml)[-1]
        lastpg = re.compile(r'class="item">\s*<a[^>]*from(?:_albums)?:(\d+)">', re.DOTALL | re.IGNORECASE).findall(listhtml)[-1]
        params = nextp[-1][1].replace(':', '=').replace(';', '&')
        if '+' in params:
            params = params.replace('+', '={0}&'.format(params.split('=')[-1].zfill(2)))
        params = params.replace('%20', '+')
        nextpg = '{0}?mode=async&function=get_block&block_id={1}&{2}'.format(url.split('?')[0], nextp[-1][0], params)
        site.add_dir('Next Page... (Currently in Page {} of {})'.format(currpg, lastpg), nextpg, 'List', site.img_next)

    utils.eod()


@site.register()
def Search(url, keyword=None):
    searchUrl = url
    if not keyword:
        site.search_dir(url, 'Search')
    else:
        title = keyword.replace(' ', '-')
        searchUrl = "{0}{1}/".format(searchUrl, title)
        List(searchUrl)


@site.register()
def TagMenu(url):
    taghtml = utils.getHtml(url, site.url)
    items = re.compile(r'data-block-id="list_tags_tags_list"\s*data-parameters="section:([^"]+)">([^<]+)', re.IGNORECASE | re.DOTALL).findall(taghtml)
    for tagpage, name in items:
        tagurl = '{0}?mode=async&function=get_block&block_id=list_tags_tags_list&section={1}&from=1&_={2}'.format(
            url,
            tagpage,
            int(time.time() * 1000)
        )
        site.add_dir(name, tagurl, 'Tag', page=1)
    utils.eod()


@site.register()
def Tag(url, page=1):
    taghtml = utils.getHtml(url, site.url)
    items = re.compile(r'item">\s+<a href="([^"]+)">\s+([^<]+)\s+<span>.+?</svg>([^<]+)<', re.IGNORECASE | re.DOTALL).findall(taghtml)
    for tagpage, name, videos in items:
        name = '{} [COLOR orange]{}[/COLOR]'.format(name.strip(), videos.strip())
        site.add_dir(name, tagpage, 'List')
    if len(items) == 120:
        nextpg = url.replace('from={}'.format(page), 'from={}'.format(page + 1))
        site.add_dir('Next Page', nextpg, 'Tag', site.img_next, page=page + 1)
    utils.eod()


@site.register()
def Cats(url):
    if '?' not in url:
        url = '{0}?mode=async&function=get_block&block_id=list_categories_categories_list&sort_by=title&_={1}'.format(
            url,
            int(time.time() * 1000)
        )
    cathtml = utils.getHtml(url, site.url)
    items = re.compile(r'item">\s*<a\s*class="th"\s*href="([^"]+).+?<img.+?src="([^"]+).+?title">([^<]+)', re.IGNORECASE | re.DOTALL).findall(cathtml)
    for catpage, img, name in items:
        name = utils.cleantext(name)
        site.add_dir(name, catpage, 'List', img)

    nextp = re.compile(r'class="item\s*pager\s*next">.+?data-parameters=.+?from:(\d+)', re.DOTALL | re.IGNORECASE).search(cathtml)

    if nextp:
        currpg = re.compile(r'class="item\s*active">.+?data-parameters=.+?from:0?(\d+)', re.DOTALL | re.IGNORECASE).findall(cathtml)[0]
        lastpg = re.compile(r'class="item">.+?data-parameters=.+?from:0?(\d+)">\s*Last', re.DOTALL | re.IGNORECASE).findall(cathtml)[-1]
        if '&from=' in url:
            nextpg = re.sub(r'&from=\d+', '', url)
        nextpg = re.sub(r'&_=\d+', '&from={0}&_={1}'.format(nextp.group(1), int(time.time() * 1000)), url)
        site.add_dir('Next Page... (Currently in Page {} of {})'.format(currpg, lastpg), nextpg, 'Cats', site.img_next)

    utils.eod()


@site.register()
def Playvid(url, name, download=None):
    vp = utils.VideoPlayer(name, download)
    vp.progress.update(25, "[CR]Loading video page[CR]")
    vpage = utils.getHtml(url, site.url)
    if "kt_player('kt_player'" in vpage:
        vp.progress.update(60, "[CR]{0}[CR]".format("kt_player detected"))
        vp.play_from_kt_player(vpage, url)


@site.register()
def Lookupinfo(url):
    lookup_list = [
        ("Artist", r'video_meta_pill" href="https://rule34video.com/(models/[^"]+)">.+?alt="([^"]+)"', ''),
        ("Categorie", r'video_meta_pill" href="https://rule34video.com/(categories/[^"]+)">.+?alt="([^"]+)"', ''),
        ("Uploaded by", r'video_meta_pill" href="https://rule34video.com/(members/[^"]+)">.+?alt="([^"]+)"', ''),
        ("Tag", r'class="tag_item" href="https://rule34video.com/(tags/[^"]+)">([^<]+)<', ''),
    ]
    lookupinfo = utils.LookupInfo(site.url, url, 'rule34video.List', lookup_list)
    lookupinfo.getinfo()
