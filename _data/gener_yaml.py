#!/usr/bin/env python3

import argparse
import collections
import json
import re
import os
import sys
import time
import yaml

import urllib.request
import xml.etree.ElementTree as ET

KEY_FIELD_NAME = '0KEY_'


def merge_dicts(m1, m2):
    for k,v in m2.items():
        if k not in m1:
            m1[k] = v
    return m1


def parse_argv(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--yaml-template', dest='yaml_template',
                        action='store', required=True)
    parser.add_argument('--cache-fname', dest='cache_fname',
                        action='store', required=False, default=None)
    return parser.parse_args(argv)


def load_cache(cache_fname):
    cache = {}
    if os.path.isfile(cache_fname):
        with open(cache_fname, 'rt') as f:
            for line in f:
                r = json.loads(line)
                key = r[KEY_FIELD_NAME]
                cache[key] = r
    return cache


def save_cache(cache_fname, cache):

    with open(cache_fname, 'wt') as f:
        for k in sorted(cache.keys()):
            f.write(json.dumps(cache[k], sort_keys=True)+'\n')


def extract_metadata(line):
    ENUMERATION_CHARS = { '+' }
    BEG_REFERENCE_CHAR = '{'
    END_REFERENCE_CHAR = '}'

    def _get_line_prefix(line, enumerator_char):
        return line.split(sep=enumerator_char, maxsplit=1)[0]

    res = None
    line_stripped = line.strip()
    if line_stripped and line_stripped[0] in ENUMERATION_CHARS:
        line_reference = line_stripped[1:].strip()
        if (line_reference[0] == BEG_REFERENCE_CHAR and line_reference[-1] == END_REFERENCE_CHAR):
            enumerator_char = line_stripped[0]
            res = json.loads(line_reference)
            res['enumerator_char'] = enumerator_char
            res['line_prefix'] = _get_line_prefix(line, enumerator_char)
    return res


def get_cache_key(src_code, src_id):
    return  src_code + ':' + src_id


def parse_generic_xml(root):

    ATTRIB_KEY = '_attrib'

    def _normalize_tag(s):
        i = s.rfind('}')
        return s[(i+1):]

    def _insert_and_listify(res, key, val):

        if key in res:
            val_cur = res[key]
            if isinstance(val_cur, list):
                res[key].append(val)
            else:
                res[key] = [val_cur] + [val]
        else:
            res[key] = val
        return res

    res = {}

    for child in root:
        if len(child) > 0:
            key = _normalize_tag(child.tag)
            val = parse_generic_xml(child)
            if len(child.attrib) > 0:
                val[ATTRIB_KEY] = child.attrib
            res = _insert_and_listify(res, key, val)
        else:
            key = _normalize_tag(child.tag)
            val = child.text
            if len(child.attrib) > 0:
                val_new = { 'val': val, ATTRIB_KEY: child.attrib }
                val = val_new
            res = _insert_and_listify(res, key, val)
    return res


def fetch_raw_metadata_arxiv(src_id):
    OAI_PMH_URL = 'http://export.arxiv.org/oai2'
    QUERY_FORMAT = '?verb=GetRecord&identifier=oai:arXiv.org:%s&metadataPrefix=arXiv'

    query = QUERY_FORMAT % src_id
    finished = False
    while not finished:
        try:
            url = OAI_PMH_URL + query
            #print('Fetching %s' % url, file=sys.stderr)
            result = urllib.request.urlopen(url).read()
            time.sleep(5)
            finished = True
        except urllib.error.HTTPError as e:
            if e.code == 503:
                retry_after = int(e.headers['Retry-After'])
                print('Sleeping %d...' % retry_after, file=sys.stderr)
                time.sleep(retry_after)
            else:
                raise e
    res=parse_generic_xml(ET.fromstring(result))
    return res


def clean_raw_metadata_arxiv(met_raw):

    def _normalize_title(title):
        title_norm = title.replace('\n', ' ')
        title_norm = re.sub(r' +', ' ', title_norm)
        return title_norm


    def _normalize_authors(authors):
        return [ [ a['keyname'], a['forenames'] ] for a in authors ]


    def _normalize_arxiv_id(arxiv_id):
        return arxiv_id.replace('oai:arXiv.org:', '')


    met = {}
    title_raw = met_raw['GetRecord']['record']['metadata']['arXiv']['title']
    authors_raw = met_raw['GetRecord']['record']['metadata']['arXiv']['authors']['author']
    if not isinstance(authors_raw, collections.abc.Sequence):
        authors_raw = [ authors_raw ]
    met['title'] = _normalize_title(title_raw)
    met['authors'] = _normalize_authors(authors_raw)
    arxiv_id_raw = met_raw['GetRecord']['record']['header']['identifier']
    met['arxiv_id'] = _normalize_arxiv_id(arxiv_id_raw)
    met['year'] = met_raw['GetRecord']['record']['metadata']['arXiv']['created'][0:4]
    try:
        doi = met_raw['GetRecord']['record']['metadata']['arXiv']['doi']
        met['doi'] = doi
    except Exception as e:
        met['doi'] = None
    return met


def fetch_raw_metadata_doi(src_id):
    CROSSREF_API_URL = 'http://api.crossref.org/works/'

    url = CROSSREF_API_URL + src_id
    #print('Fetching %s' % url, file=sys.stderr)
    result = urllib.request.urlopen(url).read()
    time.sleep(5)
    finished = True
    return json.loads(result.decode('utf-8'))


def clean_raw_metadata_doi(met_raw):
    title_parts = met_raw['message']['title']

    met = {}

    title=''
    for t in title_parts:
        title += ' ' + t

    authors  =[ [ a['family'], a['given'] ]  for a in met_raw['message']['author'] ]

    met['title'] = title[1:]
    met['authors'] = authors
    met['doi'] =  met_raw['message']['DOI']
    return met


def fetch_raw_metadata_sems(src_id):
    SEMS_API_URL = 'http://api.semanticscholar.org/v1/paper/'

    url = SEMS_API_URL + src_id
    #print('Fetching %s' % url, file=sys.stderr)
    result = urllib.request.urlopen(url).read()
    time.sleep(5)
    finished = True
    res = json.loads(result.decode('utf-8'))
    res['sems_id'] = src_id
    return res


def clean_raw_metadata_sems(met_raw):
    met = {}

    authors = []
    for a in met_raw['authors']:
        a_split = a['name'].split()
        a = [a_split[-1]] + a_split[:-1]
        authors.append(a)
    met['authors'] = authors
    met['title'] = met_raw['title']
    met['sems_id'] = met_raw['sems_id']

    if 'arxivId' in met_raw:
        met['arxiv_id'] = met_raw['arxivId']
    if 'doi' in met_raw:
        met['doi'] = met_raw['doi']
    if 'year' in met_raw:
        met['year'] = met_raw['year']

    return met


def convert_metadata_to_lines(m):
    content = m['line_prefix'] + m['enumerator_char'] + ' ' + m['title']
    authors = ''

    for a in m['authors']:
        authors += ', ' + a[1] + ' ' + a[0]
    content += ' by ' + authors[2:] + '\n'
    prefix =  m['line_prefix'] + '  '  + m['enumerator_char'] + ' '
    arxiv_id = m.get('arxiv_id', None)
    if arxiv_id is not None:
        content += prefix + 'https://arxiv.org/pdf/' + arxiv_id + '\n'
    doi = m.get('doi', None)
    if doi is not None:
        content += prefix + 'https://dx.doi.org/' + doi + '\n'
    return content


def fetch_metadata_cached(src_code, src_id, cache, fetch_raw, clean_raw):
    cache_key = get_cache_key(src_code, src_id)
    met_raw = cache.get(cache_key, None)

    if met_raw is None:
        met_raw = fetch_raw(src_id)
        met_raw[KEY_FIELD_NAME] = cache_key
        cache[cache_key] = met_raw
    met = clean_raw(met_raw)
    return met


def enrich_metadata_dict(m, cache):

    def _extract_authors(m):
        res = None
        authors = m.get('authors', None)
        if authors is not None:
            if len(authors) == 1:
                res = authors[0][0]
            elif len(authors) == 2:
                res = authors[0][0] + ' and ' + authors[1][0]
            elif len(authors) > 2:
                res = authors[0][0] + ' et al.'
        return res

    def _extract_url(m):
        res = None
        if  'arxiv_id' in m:
            res = 'https://arxiv.org/abs/' + m['arxiv_id']
        elif sems_id in m:
            res = '"https://www.semanticscholar.org/paper/' + m['sems_id']
        return res

    def _extract_year(m):
        res = m.get('year', None)
        if res is not None:
            res = int(res)
        return res

    def _extract_title(m):
        return m.get('title', None)

    def _merge_metadata(m, m1, field_pairs):
        for k, fn_val in field_pairs:
            if k not in m:
                val = fn_val(m1)
                if val is not None:
                    m[k] = val
        return m

    FIELD_PAIRS = [ [ 'paper', _extract_title ],
                    [ 'authors', _extract_authors ],
                    [ 'year', _extract_year ],
                    [ 'url', _extract_url ] ]

    arxiv_id = m.get('arxiv_id', None)
    m_arx = {}
    if arxiv_id is not None:
        m_arx = fetch_metadata_cached(
                    src_code='a', src_id=arxiv_id,
                    fetch_raw=fetch_raw_metadata_arxiv,
                    clean_raw=clean_raw_metadata_arxiv,
                    cache=cache)

    sems_id = m.get('sems_id', None)
    m_sems = {}
    if sems_id is not None:
        m_sems = fetch_metadata_cached(
                    src_code='s', src_id=sems_id,
                    fetch_raw=fetch_raw_metadata_sems,
                    clean_raw=clean_raw_metadata_sems,
                    cache=cache)
    m = _merge_metadata(m, m_arx, FIELD_PAIRS)
    m = _merge_metadata(m, m_sems, FIELD_PAIRS)
    return m


def enrich_metadata(metadata, cache):
    if isinstance(metadata, list):
        res = []
        for d in metadata:
            res.append(enrich_metadata(d, cache))
    elif isinstance(metadata, dict):
        res = {}
        for (k, d) in metadata.items():
            res[k] = enrich_metadata(d, cache)
        enrich_metadata_dict(res, cache)
    else:
        res = metadata
    return res


def main(args):
    cache = {}
    if args.cache_fname is not None:
        cache = load_cache(args.cache_fname)
    n0_cache = len(cache)

    with open(args.yaml_template, 'r') as f:
        metadata = yaml.load(f)
    enriched_metadata = enrich_metadata(metadata, cache)
    print(yaml.dump(enriched_metadata))

    if args.cache_fname is not None and n0_cache != len(cache):
        save_cache(args.cache_fname, cache)


if __name__ == '__main__':
    args = parse_argv(sys.argv[1:])
    main(args)
