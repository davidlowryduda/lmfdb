# -*- coding: utf-8 -*-
from six.moves import range
import itertools, re

from flask import render_template, url_for, redirect, request, jsonify
from psycopg2.extensions import QueryCanceledError
from sage.all import ZZ, QQ, cos, sin, pi, list_plot, circle, line2d, cached_function

from lmfdb import db
from lmfdb.app import ctx_proc_userdata
from lmfdb.utils import (
    to_dict, encode_plot, flash_error, display_knowl,
    SearchArray, TextBox, SelectBox, CountBox, YesNoBox,
    StatsDisplay, totaler, proportioners, prop_int_pretty,
    parse_ints, parse_rational, parse_bool, parse_count, parse_start,
    parse_ints_to_list_flash, clean_input, redirect_no_cache)
from lmfdb.utils.search_parsing import search_parser
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.galois_groups.transitive_group import smallgroup_cache, small_group_display_knowl
from lmfdb.sato_tate_groups import st_page

###############################################################################
# Globals
###############################################################################

MU_LABEL_RE = r'^0\.1\.[1-9][0-9]*$'
MU_LABEL_NAME_RE = r'^0\.1\.mu\([1-9][0-9]*\)$'
NU1_MU_LABEL_RE = r'^[1-9][0-9]*\.2\.1\.d[1-9][0-9]*$'
SU2_MU_LABEL_RE = r'^[1-9][0-9]*\.2\.3\.c[1-9][0-9]*$'
ST_LABEL_RE = r'^\d+\.\d+\.\d+\.\d+\.\d+[a-z]+$'
ST_LABEL_SHORT_RE = r'^\d+\.\d+\.\d+\.\d+\.\d+$'
ST_LABEL_NAME_RE = r'^\d+\.\d+\.[a-zA-z0-9\{\}\(\)\[\]\_\,]+'
INFINITY = -1

credit_string = 'Andrew Sutherland'

# use a list and a dictionary (for pretty printing) so that we can control the display order (switch to ordered dictionary once everyone is on python 3.1)
st0_list = ( 'SO(1)', 'U(1)', 'SU(2)', 'U(1)_2', 'SU(2)_2','U(1)xU(1)', 'U(1)xSU(2)','SU(2)xSU(2)','USp(4)' )
st0_dict = {
    'SO(1)':'\\mathrm{SO}(1)',
    'U(1)':'\\mathrm{U}(1)',
    'SU(2)':'\\mathrm{SU}(2)',
    'U(1)_2':'\\mathrm{U}(1)_2',
    'SU(2)_2':'\\mathrm{SU}(2)_2',
    'U(1)xU(1)':'\\mathrm{U}(1)\\times\\mathrm{U}(1)',
    'U(1)xSU(2)':'\\mathrm{U}(1)\\times\\mathrm{SU}(2)',
    'SU(2)xSU(2)':'\\mathrm{SU}(2)\\times\\mathrm{SU}(2)',
    'USp(4)':'\\mathrm{USp}(4)'
}

###############################################################################
# Utility functions
###############################################################################

def boolean_name(value):
    return 'yes' if value else 'no'

def comma_separated_list(list):
    return ', '.join(list)

def string_matrix(m):
    if len(m) == 0:
        return ''
    return '\\begin{bmatrix}' + '\\\\'.join('&'.join(map(str, m[i])) for i in range(len(m))) + '\\end{bmatrix}'

def get_name(label):
    if re.match(MU_LABEL_RE, label):
        name = r'\mu(%s)'%label.split('.')[2]
    elif re.match(NU1_MU_LABEL_RE, label):
        if label.split('.')[3] == 'd1':
            if label.split('.')[0] == '1':
                label = '1.2.1.2.1a'
            name = r'N(\mathrm{U}(1))'
        else:
            name = r'\mathrm{U}(1)[D_{%s}]'%label.split('.')[3][1:]
    elif re.match(SU2_MU_LABEL_RE, label):
        if label.split('.')[3] == 'c1':
            if label.split('.')[0] == '1':
                label = '1.2.3.1.1a'
            name = r'\mathrm{SU}(2)'
        else:
            name = r'\mathrm{SU}(2)[C_{%s}]'%label.split('.')[3][1:]
    else:
        data = db.gps_sato_tate.lookup(label)
        if data:
            name = data['pretty']
        else:
            name = None
    return name, label

def st_link(label):
    name, label = get_name(label)
    if name is None:
        return label
    else:
        return '<a href=%s>$%s$</a>' % (url_for('st.by_label', label=label), name)

def st_ambient(weight, degree):
    return '\\mathrm{USp}(%d)'%degree if weight%2 == 1 else '\\mathrm{O}(%d)'%degree

def trace_moments(moments):
    for m in moments:
        if m[0] == 'a_1'or m[0] == 's_1':
            return m[1:10]
    return ''

def st0_pretty(st0_name):
    if re.match(r'SO\(1\)\_\d+', st0_name):
        return r'\\mathrm{SO}(1)_{%s}' % st0_name.split('_')[1]
    if re.match(r'U\(1\)\_\d+', st0_name):
        return r'\mathrm{U}(1)_{%s}' % st0_name.split('_')[1]
    if re.match(r'SU\(2\)\_\d+', st0_name):
        return r'\mathrm{SU}(2)_{%s}' % st0_name.split('_')[1]
    return st0_dict.get(st0_name,st0_name)

def sg_pretty(sg_label):
    data = db.gps_small.lookup(sg_label)
    if data and 'pretty' in data:
        return data['pretty']
    return sg_label

# dictionary for quick and dirty prettification that does not access the database
st_pretty_dict = {
    'USp(4)':r'\mathrm{USp}(4)',
    'U(2)':r'\mathrm{U}(2)',
    'SU(2)':r'\mathrm{SU}(2)',
    'U(1)':r'\mathrm{U}(1)',
    'N(U(1))':r'N(\mathrm{U}(1))'
}

def st_pretty(st_name):
    if re.match(r'mu\([1-9][0-9]*\)', st_name):
        return '\\' + st_name
    return st_pretty_dict.get(st_name,st_name)

def st_link_by_name(weight,degree,name):
    return '<a href="%s">$%s$</a>' % (url_for('st.by_label', label="%s.%s.%s"%(weight,degree,name)), st_pretty(name))

# We want to support aliases like S3.  Ths following table is an analogue of the list of aliases in lmfdb/galois_groups/transitive_group.py, but with GAP ids as output.
aliases = {'C1': '1.1',
           'C2': '2.1',
           'C3': '3.1',
           'C4': '4.1',
           'C2^2': '4.2',
           'C2XC2': '4.2',
           'S3': '6.1',
           'C6': '6.2',
           'C2XC4': '8.2',
           'D4': '8.3',
           'C2^3': '8.5',
           'C2XC2XC2': '8.5',
           'A4': '12.3',
           'D6': '12.4',
           'C2XC6': '12.5',
           'C2XD4': '16.11',
           'S4': '24.12',
           'A4XC2': '24.13',
           'C2^2XS3': '24.14',
           'C2XC2XS3': '24.14',
           'C2XS4': '48.48'}
cyclics = {'1.1': 1,
           '2.1': 2,
           '3.1': 3,
           '4.1': 4,
           '6.2': 6}
cyclicre = r'C(\d+)'

@search_parser(clean_info=True, default_field="component_group", default_qfield="component_group", default_name="Component group")
def parse_component_group(inp, query, qfield):
    codes = inp.upper()
    ans = []
    # some commas separate groups, and others are internal to group names
    # like PSL(2,7) and gap id [6,1]
    # after upper casing, we can replace commas we want to keep with "z"
    commaid = r'\[(\d+),(\d+)\]'
    labelre = r'(\d+)\.(\d+)'
    codes = re.sub(commaid, r'\1.\2', codes)
    codes = re.sub(r'\((\d+),(\d+)\)', r'(\1z\2)', codes)
    codelist = codes.split(",")
    codelist = [code.replace("z", ",") for code in codelist]
    for code in codelist:
        # Turn zs back into commas and sort direct products
        code = "X".join(sorted(code.replace("z", ",").split("X")))
        if code in aliases:
            code = aliases[code]
        elif re.match(cyclicre, code):
            # We leave other cyclic groups intact for use in checking irrational ST groups
            # These won't match anything in the database
            pass
        elif not re.match(labelre, code):
            raise ValueError("%s is not the component group of a Sato-Tate group in the database" % code)
        ans.append(code)
    if len(ans) == 1:
        query[qfield] = ans[0]
    else:
        query[qfield] = {"$in": ans}

###############################################################################
# Learnmore display functions
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for('.completeness_page')),
            ('Source of the data', url_for('.source_page')),
            ('Reliability of the data', url_for('.reliability_page')),
            ('Sato-Tate group labels', url_for('.labels_page'))]


def learnmore_list_remove(matchstring):
    """
    Return the learnmore list with the matchstring entry removed.
    """
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

def get_bread(tail=[]):
    base = [('Sato-Tate groups', url_for('.index'))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

###############################################################################
# Pages
###############################################################################

@st_page.route('/')
def index():
    info = to_dict(request.args, search_array=STSearchArray(), stats=STStats())
    if request.args:
        return search(info)
    weight_list= [0, 1]
    degree_list = list(range(1, 5, 1))

    for key, val in [('weight_list', weight_list),
                     ('degree_list', degree_list),
                     ('st0_list', st0_list),
                     ('st0_dict', st0_dict)]:
        info[key] = val
    title = 'Sato-Tate groups'
    return render_template('st_browse.html', info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=get_bread())

@st_page.route('/random')
@redirect_no_cache
def random():
    label = db.gps_sato_tate.random()
    return url_for('.by_label', label=label)

@st_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "st_group",
        db.gps_sato_tate,
        url_for_label=lambda label: url_for('.by_label', label=label),
        title=r"Some interesting Sato-Tate groups",
        bread=get_bread("Interesting"),
        credit=credit_string,
        learnmore=learnmore_list()
    )

@st_page.route("/stats")
def statistics():
    title = "Sato-Tate groups: statistics"
    bread = get_bread("Statistics")
    return render_template("display_stats.html", info=STStats(), credit=credit_string, title=title, bread=bread, learnmore=learnmore_list())

@st_page.route('/<label>')
def by_label(label):
    clean_label = clean_input(label)
    if clean_label != label:
        return redirect(url_for('.by_label', label=clean_label), 301)
    if label == '1.2.1.d1':
        return redirect(url_for('.by_label', label='1.2.1.2.1a'), 301)
    if label == '1.2.3.c1':
        return redirect(url_for('.by_label', label='1.2.3.1.1a'), 301)
    return search_by_label(label)

###############################################################################
# Searching
###############################################################################

def search_by_label(label):
    """ search for Sato-Tate group by label and render if found """

    if re.match(ST_LABEL_RE, label):
        return render_by_label(label)
    if re.match(ST_LABEL_SHORT_RE, label):
        return redirect(url_for('.by_label',label=label+'a'),301)
    # check for labels of the form 0.1.n corresponding to mu(n)
    if re.match(MU_LABEL_RE, label):
        return render_by_label(label)
    # check for labels of the form w.2.1.dn corresponding to N(U(1)) x mu(n)
    if re.match(NU1_MU_LABEL_RE, label):
        return render_by_label(label)
    # check for labels of the form w.2.3.cn corresponding to SU(2) x mu(n)
    if re.match(SU2_MU_LABEL_RE, label):
        return render_by_label(label)
    # check for labels of the form 0.1.mu(n) (redirecto to 0.1.n)
    if re.match(MU_LABEL_NAME_RE, label):
        return redirect(url_for('.by_label',label='0.1.'+label.split('(')[1].split(')')[0]), 301)
    # check for general labels of the form w.d.name
    if re.match(ST_LABEL_NAME_RE,label):
        slabel = label.split('.')
        rlabel = db.gps_sato_tate.lucky({'weight':int(slabel[0]),'degree':int(slabel[1]),'name':slabel[2]}, "label")
        if not rlabel:
            flash_error("%s is not the label or name of a Sato-Tate group currently in the database", label)
            return redirect(url_for(".index"))
        return redirect(url_for('.by_label', label=rlabel), 301)
    # check for a straight up name
    rlabel = db.gps_sato_tate.lucky({'name':label}, "label")
    if not rlabel:
        flash_error("%s is not the label or name of a Sato-Tate group currently in the database", label)
        return redirect(url_for(".index"))
    return redirect(url_for('.by_label', label=rlabel), 301)

# This search function doesn't fit the model of search_wrapper very well,
# So we don't use it.
def search(info):
    """ query processing for Sato-Tate groups -- returns rendered results page """
    if 'jump' in info:
        return redirect(url_for('.by_label', label=info['jump']), 301)
    if 'label' in info:
        return redirect(url_for('.by_label', label=info['label']), 301)
    search_type = info.get("search_type", info.get("hst", "List"))
    template_kwds = {'bread':get_bread("Search results"),
                     'credit':credit_string,
                     'learnmore':learnmore_list()}
    title = 'Sato-Tate group search results'
    err_title = 'Sato-Tate group search input error'
    count = parse_count(info, 50)
    start = parse_start(info)
    # if user clicked refine search always restart at 0
    if 'refine' in info:
        start = 0
    ratonly = (info.get('include_irrational','no').strip().lower() == 'no')
    if search_type == "Random" and not ratonly:
        info['err'] = err = 'Cannot select random irrational Sato-Tate group'
        flash_error(err)
        return render_template('st_results.html', info=info, title=err_title, **template_kwds)
    query = {'rational':True} if ratonly else {}
    try:
        parse_ints(info,query,'weight','weight')
        if 'weight' in query:
            weight_list = parse_ints_to_list_flash(info.get('weight'),'weight')
        parse_ints(info,query,'degree','degree')
        if 'degree' in query:
            degree_list = parse_ints_to_list_flash(info.get('degree'),'degree')
        if info.get('identity_component'):
            query['identity_component'] = info['identity_component']
        parse_ints(info,query,'components','components')
        def refine_components(current, condition):
            if current is None:
                return condition
            return [x for x in condition if x in current]
        # The following are used to constraint which mu(n) will show up in search results
        components_list = None
        ommitted = set()
        if 'components' in query:
            components_list = parse_ints_to_list_flash(info.get('components'), 'components')
        parse_component_group(info,query)
        gps = query.get("component_group")
        if gps:
            if isinstance(gps, dict):
                gps = gps["$in"]
            else:
                gps = [gps]
            if not ratonly:
                cyclic_labels = set(db.gps_small.search({"cyclic": True}, "label"))
            irrat = []
            for code in gps:
                if code in cyclics:
                    irrat.append(cyclics[code])
                elif re.match(cyclicre, code):
                    irrat.append(int(code[1:]))
                elif not ratonly and code in cyclic_labels:
                    irrat.append(int(code.split(".")[0]))
            components_list = refine_components(components_list, irrat)
        parse_rational(info,query,'trace_zero_density','trace zero density')
        parse_ints(info,query,'second_trace_moment')
        parse_ints(info,query,'fourth_trace_moment')
        for name, ones in [('second_trace_moment', [1, 2]),
                           ('fourth_trace_moment', [1, 2, 4])]:
            if name in query:
                # E(x^2) for mu(1) and mu(2) are 1; others are 0
                # E(x^4) for mu(1), mu(2) and mu(4) are 1; others are 0
                E = parse_ints_to_list_flash(info.get(name), name.replace("_", " "))
                if 0 not in E:
                    components_list = refine_components(components_list, ones)
                if 1 not in E:
                    ommitted.update(ones)
        parse_ints(info,query,'first_a2_moment')
        parse_bool(info,query,'maximal')
        if "first_a2_moment" in query or query.get("maximal"):
            # mu(n) do not have a2 moments and none are maximal
            components_list = []
    except ValueError as err:
        info['err'] = str(err)
        return render_template('st_results.html', info=info, title=err_title, **template_kwds)

    # Check mu(n) groups first (these are not stored in the database)
    results = []
    if ((not 'weight' in query or 0 in weight_list) and
        (not 'degree' in query or 1 in degree_list) and
        (not 'identity_component' in query or query['identity_component'] == 'SO(1)') and
        (not 'trace_zero_density' in query or query['trace_zero_density'] == '0')):
        nres = None
        if components_list is None:
            components_list = range(1, 3 if ratonly else (start + count + 1 + len(ommitted)))
            nres = None if ratonly else INFINITY
        elif ratonly:
            components_list = [n for n in range(1,3) if n in components_list]
        components_list = [n for n in components_list if n not in ommitted]
        if nres is None:
            nres = len(components_list)
        if search_type == "Random" and nres > 0:
            # Need to return mu(1), mu(2) or mu(4) sometimes
            otherlen = db.gps_sato_tate.count(query)
            r = ZZ.random_element(nres + otherlen)
            if r < nres:
                return redirect(url_for(".by_label", label="0.1.%d" % components_list[r]), 307)
        for n in itertools.islice(components_list,start,start+count):
            results.append(mu_info(n))
    else:
        nres = 0

    if 'result_count' in info:
        nres += db.gps_sato_tate.count(query)
        return jsonify({"nres":str(nres)})
    if search_type == "Random":
        label = db.gps_sato_tate.random(query, "label")
        if label is not None:
            return redirect(url_for(".by_label", label=label), 307)

    # Now lookup other (rational) ST groups in database
    if nres != INFINITY:
        start2 = start - nres if start > nres else 0
        proj = ['label','weight','degree','real_dimension','identity_component','name','pretty','components','component_group','trace_zero_density','moments']
        try:
            res = db.gps_sato_tate.search(query, proj, limit=max(count - len(results), 0), offset=start2, info=info)
        except QueryCanceledError as err:
            ctx = ctx_proc_userdata()
            flash_error('The search query took longer than expected! Please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.' % ctx['feedbackpage'])
            info['err'] = str(err)
            return render_template('st_results.html', info=info, title=err_title, **template_kwds)
        info['number'] += nres
        if start < info['number'] and len(results) < count:
            for v in res:
                v['identity_component'] = st0_pretty(v['identity_component'])
                v['component_group'] = sg_pretty(v['component_group'])
                v['trace_moments'] = trace_moments(v['moments'])
                results.append(v)
    else:
        info['number'] = 'infinity'
    info['start'] = start
    info['count'] = count

    info['st0_list'] = st0_list
    info['st0_dict'] = st0_dict
    info['results'] = results
    info['stgroup_url'] = lambda dbc: url_for('.by_label', label=dbc['label'])
    return render_template('st_results.html', info=info, title=title, **template_kwds)

###############################################################################
# Rendering
###############################################################################

def mu_info(n):
    """ return data for ST group mu(n); for n > 2 these groups are irrational and not stored in the database """
    n = ZZ(n)
    rec = {}
    rec['label'] = "0.1.%d"%n
    rec['weight'] = 0
    rec['degree'] = 1
    rec['rational'] = boolean_name(True if n <= 2 else False)
    rec['name'] = 'mu(%d)'%n
    rec['pretty'] = r'\mu(%d)'%n
    rec['real_dimension'] = 0
    rec['components'] = int(n)
    rec['ambient'] = r'\mathrm{O}(1)' if n <= 2 else r'\mathrm{U}(1)'
    rec['connected'] = boolean_name(rec['components'] == 1)
    rec['st0_name'] = 'SO(1)'
    rec['identity_component'] = st0_pretty(rec['st0_name'])
    rec['st0_description'] = r'\mathrm{trivial}'
    rec['component_group'] = 'C_{%d}'%n
    rec['trace_zero_density']='0'
    rec['abelian'] = boolean_name(True)
    rec['cyclic'] = boolean_name(True)
    rec['solvable'] = boolean_name(True)
    rec['gens'] = r'\left[\zeta_{%d}\right]'%n
    rec['numgens'] = 1
    rec['subgroups'] = comma_separated_list([st_link("0.1.%d"%(n/p)) for p in n.prime_factors()])
    # only list supgroups with the same ambient (i.e.if mu(n) lies in O(1) don't list supgroups that are not)
    if n == 1:
        rec['supgroups'] = st_link("0.1.2")
    elif n > 2:
        rec['supgroups'] = comma_separated_list([st_link("0.1.%d"%(p*n)) for p in [2,3,5]] + [r"$\ldots$"])
    rec['moments'] = [['x'] + [ r'\mathrm{E}[x^{%d}]'%m for m in range(13)]]
    rec['moments'] += [['a_1'] + ['1' if m % n == 0  else '0' for m in range(13)]]
    rec['trace_moments'] = trace_moments(rec['moments'])
    rational_traces = [1] if n%2 else [1,-1]
    rec['counts'] = [['a_1', [[t,1] for t in rational_traces]]]
    rec['probabilities'] = [[r'\mathrm{Pr}[a_1=%d]=\frac{1}{%d}'%(m,n)] for m in rational_traces]
    return rec

def mu_portrait(n):
    """ returns an encoded scatter plot of the nth roots of unity in the complex plane """
    if n <= 120:
        plot =  list_plot([(cos(2*pi*m/n),sin(2*pi*m/n)) for m in range(n)],pointsize=30+60/n,axes=False)
    else:
        plot = circle((0,0),1,thickness=3)
    plot.xmin(-1); plot.xmax(1); plot.ymin(-1); plot.ymax(1)
    plot.set_aspect_ratio(4.0/3.0)
    plot.axes(False)
    return encode_plot(plot)

def su2_mu_info(w,n):
    """ return data for ST group SU(2) x mu(n) (of any wt > 0); these groups are not stored in the database """
    assert w > 0 and n > 0
    n = ZZ(n)
    rec = {}
    rec['label'] = "%d.2.3.c%d"%(w,n)
    rec['weight'] = w
    rec['degree'] = 2
    rec['rational'] = boolean_name(True if n <= 2 else False)
    rec['name'] = 'SU(2)[C%d]'%n if n > 1 else 'SU(2)'
    rec['pretty'] = r'\mathrm{SU}(2)[C_{%d}]'%n if n > 1 else r'\mathrm{SU}(2)'
    rec['real_dimension'] = 3
    rec['components'] = int(n)
    rec['ambient'] = r'\mathrm{U}(2)'
    rec['connected'] = boolean_name(rec['components'] == 1)
    rec['st0_name'] = 'SU(2)'
    rec['identity_component'] = st0_pretty(rec['st0_name'])
    rec['st0_description'] = r'\left\{\begin{bmatrix}\alpha&\beta\\-\bar\beta&\bar\alpha\end{bmatrix}:\alpha\bar\alpha+\beta\bar\beta = 1,\ \alpha,\beta\in\mathbb{C}\right\}'
    rec['component_group'] = 'C_{%d}'%n
    rec['abelian'] = boolean_name(True)
    rec['cyclic'] = boolean_name(True)
    rec['solvable'] = boolean_name(True)
    rec['trace_zero_density']='0'
    rec['gens'] = r'\begin{bmatrix} 1 & 0 \\ 0 & \zeta_{%d}\end{bmatrix}'%n
    rec['numgens'] = 1
    rec['subgroups'] = comma_separated_list([st_link("%d.2.3.c%d"%(w,n/p)) for p in n.prime_factors()])
    rec['supgroups'] = comma_separated_list([st_link("%d.2.3.c%d"%(w,p*n)) for p in [2,3,5]] + [r"$\ldots$"])
    rec['moments'] = [['x'] + [ r'\mathrm{E}[x^{%d}]'%m for m in range(13)]]
    su2moments = ['1','0','1','0','2','0','5','0','14','0','42','0','132']
    rec['moments'] += [['a_1'] + [su2moments[m] if m % n == 0  else '0' for m in range(13)]]
    rec['trace_moments'] = trace_moments(rec['moments'])
    rec['counts'] = []
    return rec

def su2_mu_portrait(n):
    """ returns an encoded line plot of SU(2) x mu(n) in the complex plane """
    if n == 1:
        return db.gps_sato_tate.lookup('1.2.3.1.1a').get('trace_histogram')
    if n <= 120:
        plot =  sum([line2d([(-2*cos(2*pi*m/n),-2*sin(2*pi*m/n)),(2*cos(2*pi*m/n),2*sin(2*pi*m/n))],thickness=3) for m in range(n)])
    else:
        plot = circle((0,0),2,fill=True)
    plot.xmin(-2); plot.xmax(2); plot.ymin(-2); plot.ymax(2)
    plot.set_aspect_ratio(4.0/3.0)
    plot.axes(False)
    return encode_plot(plot)


def nu1_mu_info(w,n):
    """ return data for ST group N(U(1)) x mu(n) (of any wt > 0); these groups are not stored in the database """
    assert w > 0 and n > 0
    n = ZZ(n)
    rec = {}
    rec['label'] = "%d.2.1.d%d"%(w,n)
    rec['weight'] = w
    rec['degree'] = 2
    rec['rational'] = boolean_name(True if n <= 2 else False)
    rec['name'] = 'U(1)[D%d]'%n if n > 1 else 'N(U(1))'
    rec['pretty'] = r'\mathrm{U}(1)[D_{%d}]'%n if n > 1 else r'N(\mathrm{U}(1))'
    rec['real_dimension'] = 1
    rec['components'] = int(2*n)
    rec['ambient'] = r'\mathrm{U}(2)'
    rec['connected'] = boolean_name(rec['components'] == 1)
    rec['st0_name'] = 'U(1)'
    rec['identity_component'] = st0_pretty(rec['st0_name'])
    rec['st0_description'] = r'\left\{\begin{bmatrix}\alpha&0\\0&\bar\alpha\end{bmatrix}:\alpha\bar\alpha = 1,\ \alpha\in\mathbb{C}\right\}'
    rec['component_group'] = 'D_{%d}'%n
    rec['abelian'] = boolean_name(n <= 2)
    rec['cyclic'] = boolean_name(n <= 1)
    rec['solvable'] = boolean_name(True)
    rec['trace_zero_density']='1/2'
    rec['gens'] = r'\left\{\begin{bmatrix} 0 & 1\\ -1 & 0\end{bmatrix}, \begin{bmatrix} 1 & 0 \\ 0 & \zeta_{%d}\end{bmatrix}\right\}'%n
    rec['numgens'] = 2
    rec['subgroups'] = comma_separated_list([st_link("%d.2.1.d%d"%(w,n/p)) for p in n.prime_factors()])
    rec['supgroups'] = comma_separated_list([st_link("%d.2.1.d%d"%(w,p*n)) for p in [2,3,5]] + [r"$\ldots$"])
    rec['moments'] = [['x'] + [ r'\mathrm{E}[x^{%d}]'%m for m in range(13)]]
    nu1moments = ['1','0','1','0','3','0','10','0','35','0','126','0','462']
    rec['moments'] += [['a_1'] + [nu1moments[m] if m % n == 0  else '0' for m in range(13)]]
    rec['trace_moments'] = trace_moments(rec['moments'])
    rec['counts'] = [['a_1', [[0,n]]]]
    return rec

def nu1_mu_portrait(n):
    """ returns an encoded scatter plot of the nth roots of unity in the complex plane """
    if n == 1:
        return db.gps_sato_tate.lookup('1.2.1.2.1a').get('trace_histogram')
    if n <= 120:
        plot =  sum([line2d([(-2*cos(2*pi*m/n),-2*sin(2*pi*m/n)),(2*cos(2*pi*m/n),2*sin(2*pi*m/n))],thickness=3) for m in range(n)]) + circle((0,0),0.1,rgbcolor=(0,0,0),fill=True)
    else:
        plot = circle((0,0),2,fill=True)
    plot.xmin(-2); plot.xmax(2); plot.ymin(-2); plot.ymax(2)
    plot.set_aspect_ratio(4.0/3.0)
    plot.axes(False)
    return encode_plot(plot)

def render_by_label(label):
    """ render html page for Sato-Tate group sepecified by label """
    if re.match(MU_LABEL_RE, label):
        n = ZZ(label.split('.')[2])
        if n > 10**20:
            flash_error("number of components %s is too large, it should be less than 10^{20}$.", n)
            return redirect(url_for(".index"))
        return render_st_group(mu_info(n), portrait=mu_portrait(n))
    if re.match(NU1_MU_LABEL_RE, label):
        w = ZZ(label.split('.')[0])
        n = ZZ(label.split('.')[3][1:])
        if 2*n > 10**20:
            flash_error("number of components %s is too large, it should be less than 10^{20}$.", 2*n)
            return redirect(url_for(".index"))
        return render_st_group(nu1_mu_info(w,n), portrait=nu1_mu_portrait(n))
    if re.match(SU2_MU_LABEL_RE, label):
        w = ZZ(label.split('.')[0])
        n = ZZ(label.split('.')[3][1:])
        if n > 10**20:
            flash_error("number of components %s is too large, it should be less than 10^{20}$.", n)
            return redirect(url_for(".index"))
        return render_st_group(su2_mu_info(w,n), portrait=su2_mu_portrait(n))
    data = db.gps_sato_tate.lookup(label)
    info = {}
    if data is None:
        flash_error ("%s is not the label of a Sato-Tate group currently in the database.", label)
        return redirect(url_for(".index"))
    for attr in ['label','weight','degree','name','pretty','real_dimension','components']:
        info[attr] = data[attr]
    info['ambient'] = st_ambient(info['weight'],info['degree'])
    info['connected']=boolean_name(info['components'] == 1)
    info['rational']=boolean_name(info.get('rational',True))
    st0 = db.gps_sato_tate0.lucky({'name':data['identity_component']})
    if not st0:
        flash_error ("%s is not the label of a Sato-Tate identity component currently in the database.", data['identity_component'])
        return redirect(url_for(".index"))
    info['st0_name']=st0['name']
    info['identity_component']=st0['pretty']
    info['st0_description']=st0['description']
    G = db.gps_small.lookup(data['component_group'])
    if not G:
        flash_error ("%s is not the label of a Sato-Tate component group currently in the database.", data['component_group'])
        return redirect(url_for(".index"))
    info['component_group']=G['pretty']
    info['cyclic']=boolean_name(G['cyclic'])
    info['abelian']=boolean_name(G['abelian'])
    info['solvable']=boolean_name(G['solvable'])
    info['gens']=comma_separated_list([string_matrix(m) for m in data['gens']])
    info['numgens']=len(info['gens'])
    if data.get('subgroup_multiplicities'):
        mults = ["${}^{\\times %d}$"%m if m >1 else "" for m in data['subgroup_multiplicities']]
    else:
        mults = ["" for s in data['subgroups']]
    info['subgroups'] = comma_separated_list([st_link(data['subgroups'][i]) + mults[i] for i in range(len(mults))])
    info['supgroups'] = comma_separated_list([st_link(sup) for sup in data['supgroups']])
    if data['moments']:
        info['moments'] = [['x'] + [ '\\mathrm{E}[x^{%d}]'%m for m in range(len(data['moments'][0])-1)]]
        info['moments'] += data['moments']
    if data['simplex']:
        if data['degree'] == 4:
            info['simplex_header'] = ["\\left(\\mathrm{E}[a_1^{e_1}a_2^{e_2}):\\sum ie_i=%d\\right]\\colon"%(2*d+2) for d in range(len(data['simplex']))]
            s = data['simplex']
            t = [s[0:2]]
            m,n=2,3
            while m+n < len(s):
                t += [s[m:m+n]]
                m,n = m+n,n+1
            info['simplex'] = t
    if data['counts']:
        c=data['counts']
        info['probabilities'] = [['\\mathrm{Pr}[%s=%d]=\\frac{%d}{%d}'%(c[i][0],c[i][1][j][0],c[i][1][j][1],data['components']) for j in range(len(c[i][1]))] for i in range(len(c))]
    return render_st_group(info, portrait=data.get('trace_histogram'))

def render_st_group(info, portrait=None):
    """ render html page for Sato-Tate group described by info """
    prop2 = [('Label', '%s'%info['label'])]
    if portrait:
        prop2 += [(None, '&nbsp;&nbsp;<img src="%s" width="220" height="124"/>' % portrait)]
    prop2 += [
        ('Name', r'\(%s\)'%info['pretty']),
        ('Weight', prop_int_pretty(info['weight'])),
        ('Degree', prop_int_pretty(info['degree'])),
        ('Real dimension', prop_int_pretty(info['real_dimension'])),
        ('Components', prop_int_pretty(info['components'])),
        ('Contained in',r'\(%s\)'%info['ambient']),
        ('Identity component', r'\(%s\)'%info['identity_component']),
        ('Component group', r'\(%s\)'%info['component_group']),
    ]
    bread = get_bread([
        ('Weight %d'% info['weight'], url_for('.index')+'?weight='+str(info['weight'])),
        ('Degree %d'% info['degree'], url_for('.index')+'?weight='+str(info['weight'])+'&degree='+str(info['degree'])),
        (info['name'], '')
    ])
    title = r'Sato-Tate group \(' + info['pretty'] + r'\) of weight %d'% info['weight'] + ' and degree %d'% info['degree']
    return render_template('st_display.html',
                           properties=prop2,
                           credit=credit_string,
                           info=info,
                           bread=bread,
                           learnmore=learnmore_list(),
                           title=title,
                           KNOWL_ID='st_group.%s'%(info['label']))

@st_page.route('/Completeness')
def completeness_page():
    t = 'Completeness of Sato-Tate group data'
    bread = get_bread("Completeness")
    return render_template('single.html', kid='rcs.cande.st_group',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@st_page.route('/Source')
def source_page():
    t = 'Source of Sato-Tate group data'
    bread = get_bread("Source")
    return render_template('single.html', kid='rcs.source.st_group',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@st_page.route('/Reliability')
def reliability_page():
    t = 'Reliability of Sato-Tate group data'
    bread = get_bread("Reliability")
    return render_template('single.html', kid='rcs.rigor.st_group',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@st_page.route('/Labels')
def labels_page():
    t = 'Labels for Sato-Tate groups'
    bread = get_bread("Labels")
    return render_template('single.html', kid='st_group.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

class STSearchArray(SearchArray):
    noun = "group"
    plural_noun = "groups"
    jump_example = "1.4.USp(4)"
    jump_egspan = "e.g. 0.1.3 or 0.1.mu(3), or 1.2.1.2.1a or N(U(1)), or 1.4.10.1.1a or 1.4.USp(4)"
    jump_knowl = "st_group.search_input"
    jump_prompt = "Label or name"
    def __init__(self):
        weight = TextBox(
            name="weight",
            label="Weight",
            knowl="st_group.weight",
            example="1",
            example_span="1 or 0-3")
        degree = TextBox(
            name="degree",
            label="Degree",
            knowl="st_group.degree",
            example="4",
            example_span="4 or 1-6")
        include_irrational = SelectBox(
            name="include_irrational",
            label="Include irrational",
            knowl="st_group.rational",
            example_col=True,
            options=[("", "no"),
                     ("yes", "yes")])
        identity_component = SelectBox(
            name="identity_component",
            label="Identity component",
            short_label=r"$\mathrm{ST}^0$",
            knowl="st_group.identity_component",
            example_span="U(1) or USp(4)",
            options=[("", "")] + [(r, r) for r in st0_list])
        components = TextBox(
            name="components",
            label="Components",
            knowl="st_group.components",
            example="1",
            example_span="1 (connected) or 4-12")
        trace_zero_density = TextBox(
            name="trace_zero_density",
            label="Trace zero density",
            knowl="st_group.trace_zero_density",
            short_label=r"$\mathrm{Pr}[a_1=0]$",
            example="1/2",
            example_span="0, 1/2, or 3/8")
        second_trace_moment = TextBox(
            name="second_trace_moment",
            label="Second trace moment",
            knowl="st_group.moments",
            example="8")
        fourth_trace_moment = TextBox(
            name="fourth_trace_moment",
            label="Fourth trace moment",
            knowl="st_group.moments",
            example="96")
        first_a2_moment = TextBox(
            name="first_a2_moment",
            label="First $a_2$ moment",
            knowl="st_group.moments",
            example="4")
        maximal = YesNoBox(
            name="maximal",
            label="Maximal",
            knowl="st_group.supgroups",
            example_col=True)
        component_group = TextBox(
            name="component_group",
            label="Component group",
            knowl="st_group.component_group",
            example="[48,48]",
            example_span="list of %s, e.g. [8,3], or %s, e.g. S4." % (display_knowl("group.small_group_label", "GAP ids"), display_knowl("nf.galois_group.name", "group labels")))
        count = CountBox()

        self.browse_array = [
            [weight, trace_zero_density],
            [degree, second_trace_moment],
            [include_irrational, fourth_trace_moment],
            [identity_component, first_a2_moment],
            [maximal, components],
            [count, component_group]]

        self.refine_array = [[weight, degree, include_irrational, identity_component, maximal], [components, component_group, trace_zero_density, second_trace_moment, fourth_trace_moment], [first_a2_moment]]

@cached_function
def compcache():
    return smallgroup_cache(db.gps_sato_tate.distinct("component_group"))
gapidre = re.compile(r"(\d+)\.(\d+)")
def compdata(comp):
    return [int(x) for x in gapidre.findall(comp)[0]]
def compformatter(comp):
    n, k = compdata(comp)
    return small_group_display_knowl(n, k, cache=compcache())
def compunformatter(comp):
    n, k = compdata(comp)
    return "%d.%d" % (n, k)
def idformatter(grp):
    return "$%s$" % (r"\operatorname{" + grp.replace("x", r"\times\operatorname{").replace("(", "}("))
def idunformatter(grp):
    return grp.replace("$", "").replace(r"\operatorname", "").replace(r"\times", "x").replace("{", "").replace("}", "")

class STStats(StatsDisplay):
    table = db.gps_sato_tate
    baseurl_func = ".index"

    stat_list = [
        {"cols": ["component_group", "identity_component"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["identity_component"],
         "constraint": {"maximal": True},
         "top_title": [("maximal subgroups", "st_group.supgroups"),
                       ("per", None),
                       ("identity component", "st_group.identity_component")],
        },
        {"cols": ["trace_zero_density", "identity_component"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["second_trace_moment", "identity_component"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["fourth_trace_moment", "identity_component"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
        {"cols": ["first_a2_moment", "identity_component"],
         "totaler": totaler(),
         "proportioner": proportioners.per_col_total},
    ]

    formatters = {"component_group": compformatter,
                  "identity_component": idformatter}
    sort_keys = {"component_group": compdata,
                 "trace_zero_density": QQ}
    query_formatters = {"component_group": (lambda comp: "component_group=%s" % compunformatter(comp)),
                        "identity_component": (lambda grp: "identity_component=%s" % (idunformatter(grp)))}
    top_titles = {"trace_zero_density": "trace zero densities",
                  "first_a2_moment": "first $a_2$ moment"}
    knowls = {"identity_component": "st_group.identity_component",
              "component_group": "st_group.component_group",
              "trace_zero_density": "st_group.trace_zero_density",
              "second_trace_moment": "st_group.moments",
              "fourth_trace_moment": "st_group.moments",
              "first_a2_moment": "st_group.moments"}

    def __init__(self):
        self.ngroups = db.gps_sato_tate.count()

    @property
    def summary(self):
        return r"The database currently contains %s %s.  The statistics below omit the infinite family $\mu(n)$ with trivial %s since they are generated dynamically in search results." % (
            self.ngroups,
            display_knowl('st_group.definition', 'Sato-Tate groups'),
            display_knowl('st_group.identity_component', 'identity component'))

    @property
    def short_summary(self):
        return r'The database currently contains all %s %s of %s 1 and %s up to 4, as well as all Sato-Tate groups of weight 0 and degree 1 with %s of order at most $10^{20}$.  Here are some <a href="%s">further statistics</a>.' % (
            display_knowl('st_group.rational', 'rational'),
            display_knowl('st_group.definition', 'Sato-Tate groups'),
            display_knowl('st_group.weight', 'weight'),
            display_knowl('st_group.degree', 'degree'),
            display_knowl('st_group.component_group', 'component group'),
            url_for('.statistics'))
