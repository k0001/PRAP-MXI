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

from __future__ import absolute_import

import csv
import json
import logging
import os
import time
import html5lib
from prap.crawler import Job
from prap.utils import whitespace_cleanup, force_unicode, digits_only, flip_flop


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)



# Cargar distritos desde el CSV
DISTRITOS = {}
csv_path = os.path.join(os.path.dirname(__file__), 'distritos.csv')
with open(csv_path, 'rb') as f:
    cr = csv.reader(f)
    assert next(cr) == ['id', 'nombre']
    for row in cr:
        k, v = row[0], row[1].decode('utf-8')
        DISTRITOS[k] = v
log.info(u"%s: Cargados %d distritos" % (csv_path, len(DISTRITOS)))


CARGOS = {
    'PR': u"Presidente",
    'SN': u"Senador Nacional",
    'DN': u"Diputado Nacional",
    'GO': u"Gobernador",
    'SP': u"Senador Provincial",
    #'SP': u"Diputado Proporcional" en la provincia 18 (San Juan)
    'DP': u"Diputado Provincial",
    #'DP': u"Diputado Departamental" en la provincia 18 (San Juan)
}

CARGOS_POR_PROVINCIA = {
    '99': ['PR'                              ],
    '01': ['PR',       'DN'                  ],
    '02': ['PR', 'SN', 'DN', 'GO', 'SP', 'DP'],
    '02': ['PR',       'DN'                  ],
    '03': ['PR',       'DN'                  ],
    '04': ['PR',       'DN'                  ],
    '05': ['PR',       'DN'                  ],
    '06': ['PR',       'DN'                  ],
    '07': ['PR',       'DN'                  ],
    '08': ['PR',       'DN'                  ],
    '09': ['PR', 'SN', 'DN'                  ],
    '10': ['PR', 'SN', 'DN'                  ],
    '11': ['PR',       'DN'                  ],
    '12': ['PR', 'SN', 'DN'                  ],
    '13': ['PR',       'DN'                  ],
    '14': ['PR', 'SN', 'DN'                  ],
    '15': ['PR',       'DN'                  ],
    '16': ['PR',       'DN'                  ],
    '17': ['PR',       'DN'                  ],
    '18': ['PR', 'SN', 'DN', 'GO', 'SP', 'DP'],
    '19': ['PR', 'SN', 'DN'                  ],
    '20': ['PR', 'SN', 'DN'                  ],
    '21': ['PR',       'DN'                  ],
    '22': ['PR',       'DN'                  ],
    '23': ['PR',       'DN'                  ],
    '24': ['PR',       'DN'                  ],
}



def c(text, encoding='iso8859-1'):
    """Simple text cleanup utility fit for our purposes"""
    return whitespace_cleanup(force_unicode(text, encoding=encoding))


class Spider(object):
    URL_BASE = "http://www.primarias2011.gob.ar/paginas/paginas"
    URL_RESULTS_TMPL = (URL_BASE + "/dat%(prov_id)s"
                                   "/D%(cargo_id)s%(distrito_id)s.htm")

    def __init__(self, out_file):
        self.urls = []
        self._populate_start_jobs()
        self._out_file = out_file

    def _populate_start_jobs(self):
        if not hasattr(self, 'jobs'):
            self.jobs = []
        for distrito_id in sorted(DISTRITOS):
            prov_id = distrito_id[:2]
            for cargo_id in CARGOS_POR_PROVINCIA[prov_id]:
                if prov_id == '18' and cargo_id == 'SP':
                    # Parsing Exception 1: Senadores Proporcional
                    # en vez de Senadores Provinciales
                    cargo_name = u"Senador Proporcional"
                elif prov_id == '18' and cargo_id == 'DP':
                    # Parsing Exception 2: Diputados Departamental en
                    # lugar de Diputados Provinciales.
                    cargo_name = u"Diputado Departamental"
                else:
                    cargo_name = CARGOS[cargo_id]
                meta = {
                    'distrito_id': distrito_id,
                    'prov_id': prov_id,
                    'cargo_id': cargo_id,
                    'cargo_name': cargo_name }
                url_results = self.URL_RESULTS_TMPL % meta
                job = Job(url_results, meta=meta)
                self.jobs.append(job)
                log.info(u"Generated Job %s" % repr(job))

    def preprocess(self, job):
        assert (200 <= job.response.status < 300)
        out = job.meta['preprocess'] = {}
        out['votos'] = []

        doc = html5lib.parse(job.data, treebuilder='lxml',
                             namespaceHTMLElements=False)
        html = doc.getroot()

        tvotos = html.xpath('.//table[@id="TVOTOS"]')[0]
        # we skip the first <tr> since it's the title row
        # the rest of <tr> are repeated structures like this one.
        # AGRUP 1:       (a) tr
        # AGRUP 1:       (a)   th.sigla/text() -- agrupación nombre
        # AGRUP 1: [OPT] (b) tr.agrupa
        # AGRUP 1: [OPT] (b)   th.[agrupa,sigla]/text() -- agrupación lista
        # AGRUP 1: [OPT] (c) tr.agrupa
        # AGRUP 1: [OPT] (c)   th.sigla/text() -- agrupación formula
        rows = tvotos.xpath('.//tr')[1:]

        def num_votes_from_tr(tr):
            # there may be 2 <td> with class "vot", but only one won't be empty
            vot_nums = tr.xpath('./td[contanis(@class, "vot") and '
                                     'not(contains(@class, "pvot"]))]/text()')
            # Python lists need Ruby's compact method.
            vot_nums = (y for y in (digits_only(c(x)) for x in vot_nums) if y)
            assert len(vot_nums) == 1
            return int(vot_nums[0])

        oddity = lambda tr: 'r1' in tr.attrib['class']
        for trs in flip_flop(rows, oddity):
            bigrow = {}

            for tr in trs:
                if not bigrow:
                    # (a) agrupacion nombre
                    th = tr.xpath('./th[1]')[0]
                    bigrow['agrupacion'] = {'id': c(th.attrib['id']),
                                            'nombre': c(th.text)}
                else:
                    th = tr.xpath('./th[1]')[0]
                    if 'agrupa' in th.attrib['class']:
                        # (b) agrupacion lista
                        aglist = {'id': c(th.attrib['id']), 'nombre': c(th.text)}
                        if not 'listas' in bigrow:
                            bigrow['listas'] = []
                        bigrow['listas'].append(aglist)
                    else:
                        # (c) agrupacion formula
                        bigrow['formula_id'] = c(th.attrib['id'])
                        bigrow['formula_nombre'] = c(th.text)

            out['votos'].append(bigrow)
        out['timestamp'] = time.time()


    def postprocess(self, job):
        out = {'source_url': job.url}
        out.update(job.meta.pop('preprocess'))
        out.update(job.meta)
        log.info(u"Done processing %s" % out)
        json.dump(out, self._out_file, ensure_ascii=True)

