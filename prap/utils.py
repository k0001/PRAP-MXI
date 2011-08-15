# coding: utf-8

import re


def whitespace_cleanup(text):
    """Replace continuous whitespace by a single space"""
    return _re_whitespace.sub(u' ', text).strip()
_re_whitespace = re.compile(r'\s+', re.UNICODE)


def force_unicode(text, encoding='utf8'):
    """Force ``text`` to be decoded using ``encoding``, if not already decoded."""
    if not isinstance(text, unicode):
        return text.encode(encoding)
    return text

def digits_only(text):
    """Return only digits present in ``text``"""
    return unicode(x for x in text if x.isdigit())

def flip_flop(it, predicate):
    """
    Yields lists of consecutive elements from ``it`` for which the
    value of ``predicate(it)`` stays the same.
    """
    prev_result = None
    page = []
    for x in it:
        curr_result = predicate(x)
        if prev_result is None:
            # first iteration only
            prev_result = curr_result
        if prev_result == curr_result:
            page.append(x)
        elif prev_result != curr_result:
            yield page
            page = [x]
            prev_result = curr_result
    if page:
        yield page


