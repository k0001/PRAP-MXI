# coding: utf-8

# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please refer to <http://unlicense.org/>

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
    return u''.join(x for x in text if x.isdigit())

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


