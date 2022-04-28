# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/00_export.ipynb (unless otherwise specified).

__all__ = ['read_nb', 'check_re', 'check_re_multi', 'is_export', 'find_default_export', 'export_names', 'extra_add',
           'relative_import', 'reset_nbdev_module', 'get_nbdev_module', 'save_nbdev_module', 'split_flags_and_code',
           'create_mod_file', 'create_mod_files', 'add_init', 'update_version', 'update_baseurl', 'nbglob',
           'notebook2script', 'DocsTestClass']

# Cell
from .imports import *
from fastcore.script import *
from fastcore.foundation import *
from keyword import iskeyword
import nbformat

# Cell
def read_nb(fname):
    "Read the notebook in `fname`."
    with open(Path(fname),'r', encoding='utf8') as f: return nbformat.reads(f.read(), as_version=4)

# Cell
def check_re(cell, pat, code_only=True):
    "Check if `cell` contains a line with regex `pat`"
    if code_only and cell['cell_type'] != 'code': return
    if isinstance(pat, str): pat = re.compile(pat, re.IGNORECASE | re.MULTILINE)
    cell_source = cell['source'].replace('\r', '') # Eliminate \r\n
    result = pat.search(cell_source)
    return result

# Cell
def check_re_multi(cell, pats, code_only=True):
    "Check if `cell` contains a line matching any regex in `pats`, returning the first match found"
    return L(pats).map_first(partial(check_re, cell, code_only=code_only))

# Cell
def _mk_flag_re(body, n_params, comment):
    "Compiles a regex for finding nbdev flags"
    assert body!=True, 'magics no longer supported'
    prefix = r"\s*\#\|?\s*"
    param_group = ""
    if n_params == -1: param_group = r"[ \t]+(.+)"
    if n_params == 1: param_group = r"[ \t]+(\S+)"
    if n_params == (0,1): param_group = r"(?:[ \t]+(\S+))?"
    return re.compile(rf"""
# {comment}:
^            # beginning of line (since re.MULTILINE is passed)
{prefix}
{body}
{param_group}
[ \t]*       # any number of spaces and/or tabs
$            # end of line (since re.MULTILINE is passed)
""", re.MULTILINE | re.VERBOSE)

# Cell
_re_blank_export = _mk_flag_re("export[si]?", 0,
    "Matches any line with #export, #exports or #exporti without any module name")

# Cell
_re_mod_export = _mk_flag_re("export[si]?", 1,
    "Matches any line with #export, #exports or #exporti with a module name and catches it in group 1")

# Cell
_re_internal_export = _mk_flag_re("exporti", (0,1),
    "Matches any line with #exporti with or without a module name")

# Internal Cell
def _is_external_export(tst):
    "Check if a cell is an external or internal export. `tst` is an re match"
    return _re_internal_export.search(tst.string) is None

# Cell
def is_export(cell, default):
    "Check if `cell` is to be exported and returns the name of the module to export it if provided"
    tst = check_re(cell, _re_blank_export)
    if tst:
        if default is None:
            print(f"No export destination, ignored:\n{cell['source']}")
        return default, _is_external_export(tst)
    tst = check_re(cell, _re_mod_export)
    if tst: return os.path.sep.join(tst.groups()[0].split('.')), _is_external_export(tst)
    else: return None

# Cell
_re_default_exp = _mk_flag_re('default_exp', 1, "Matches any line with #default_exp with a module name")

# Cell
def find_default_export(cells):
    "Find in `cells` the default export module."
    res = L(cells).map_first(check_re, pat=_re_default_exp)
    return res.groups()[0] if res else None

# Cell
_re_patch_func = re.compile(r"""
# Catches any function decorated with @patch, its name in group 1 and the patched class in group 2
@patch         # At any place in the cell, something that begins with @patch
(?:\s*@.*)*    # Any other decorator applied to the function
\s*def         # Any number of whitespace (including a new line probably) followed by def
\s+            # One whitespace or more
([^\(\s]+)     # Catch a group composed of anything but whitespace or an opening parenthesis (name of the function)
\s*\(          # Any number of whitespace followed by an opening parenthesis
[^:]*          # Any number of character different of : (the name of the first arg that is type-annotated)
:\s*           # A column followed by any number of whitespace
(?:            # Non-catching group with either
([^,\s\(\)]*)  #    a group composed of anything but a comma, a parenthesis or whitespace (name of the class)
|              #  or
(\([^\)]*\)))  #    a group composed of something between parenthesis (tuple of classes)
\s*            # Any number of whitespace
(?:,|\))       # Non-catching group with either a comma or a closing parenthesis
""", re.VERBOSE)

# Cell
_re_typedispatch_func = re.compile(r"""
# Catches any function decorated with @typedispatch
(@typedispatch  # At any place in the cell, catch a group with something that begins with @typedispatch
\s*def          # Any number of whitespace (including a new line probably) followed by def
\s+             # One whitespace or more
[^\(]+          # Anything but whitespace or an opening parenthesis (name of the function)
\s*\(           # Any number of whitespace followed by an opening parenthesis
[^\)]*          # Any number of character different of )
\)[\s\S]*:)     # A closing parenthesis followed by any number of characters and whitespace (type annotation) and :
""", re.VERBOSE)

# Cell
_re_class_func_def = re.compile(r"""
# Catches any 0-indented function or class definition with its name in group 1
^              # Beginning of a line (since re.MULTILINE is passed)
(?:async\sdef|def|class)  # Non-catching group for def or class
\s+            # One whitespace or more
([^\(\s]+)     # Catching group with any character except an opening parenthesis or a whitespace (name)
\s*            # Any number of whitespace
(?:\(|:)       # Non-catching group with either an opening parenthesis or a : (classes don't need ())
""", re.MULTILINE | re.VERBOSE)

# Cell
_re_obj_def = re.compile(r"""
# Catches any 0-indented object definition (bla = thing) with its name in group 1
^                          # Beginning of a line (since re.MULTILINE is passed)
([_a-zA-Z]+[a-zA-Z0-9_\.]*)  # Catch a group which is a valid python variable name
\s*                        # Any number of whitespace
(?::\s*\S.*|)=  # Non-catching group of either a colon followed by a type annotation, or nothing; followed by an =
""", re.MULTILINE | re.VERBOSE)

# Cell
def _not_private(n):
    for t in n.split('.'):
        if (t.startswith('_') and not t.startswith('__')) or t.startswith('@'): return False
    return '\\' not in t and '^' not in t and '[' not in t and t != 'else'

def export_names(code, func_only=False):
    "Find the names of the objects, functions or classes defined in `code` that are exported."
    #Format monkey-patches with @patch
    def _f(gps):
        nm, cls, t = gps.groups()
        if cls is not None: return f"def {cls}.{nm}():"
        return '\n'.join([f"def {c}.{nm}():" for c in re.split(', *', t[1:-1])])

    code = _re_typedispatch_func.sub('', code)
    code = _re_patch_func.sub(_f, code)
    names = _re_class_func_def.findall(code)
    if not func_only: names += _re_obj_def.findall(code)
    return [n for n in names if _not_private(n) and not iskeyword(n)]

# Cell
_re_all_def   = re.compile(r"""
# Catches a cell with defines \_all\_ = [\*\*] and get that \*\* in group 1
^_all_   #  Beginning of line (since re.MULTILINE is passed)
\s*=\s*  #  Any number of whitespace, =, any number of whitespace
\[       #  Opening [
([^\n\]]*) #  Catching group with anything except a ] or newline
\]       #  Closing ]
""", re.MULTILINE | re.VERBOSE)

#Same with __all__
_re__all__def = re.compile(r'^__all__\s*=\s*\[([^\]]*)\]', re.MULTILINE)

# Cell
def extra_add(flags, code):
    "Catch adds to `__all__` required by a cell with `_all_=`"
    m = check_re({'source': code}, _re_all_def, False)
    if m:
        code = m.re.sub('#nbdev_' + 'comment \g<0>', code)
        code = re.sub(r'([^\n]|^)\n*$', r'\1', code)
    if not m: return [], code
    def clean_quotes(s):
        "Return `s` enclosed in single quotes, removing double quotes if needed"
        if s.startswith("'") and s.endswith("'"): return s
        if s.startswith('"') and s.endswith('"'): s = s[1:-1]
        return f"'{s}'"
    return [clean_quotes(s) for s in parse_line(m.group(1))], code

# Cell
_re_from_future_import = re.compile(r"^from[ \t]+__future__[ \t]+import.*$", re.MULTILINE)

def _from_future_import(fname, flags, code, to_dict=None):
    "Write `__future__` imports to `fname` and return `code` with `__future__` imports commented out"
    from_future_imports = _re_from_future_import.findall(code)
    if from_future_imports: code = _re_from_future_import.sub('#nbdev' + '_comment \g<0>', code)
    else: from_future_imports = _re_from_future_import.findall(flags)
    if not from_future_imports or to_dict is not None: return code
    with open(fname, 'r', encoding='utf8') as f: text = f.read()
    start = _re__all__def.search(text).start()
    with open(fname, 'w', encoding='utf8') as f:
        f.write('\n'.join([text[:start], *from_future_imports, '\n', text[start:]]))
    return code

# Cell
def _add2all(fname, names, line_width=120):
    if len(names) == 0: return
    with open(fname, 'r', encoding='utf8') as f: text = f.read()
    tw = TextWrapper(width=120, initial_indent='', subsequent_indent=' '*11, break_long_words=False)
    re_all = _re__all__def.search(text)
    start,end = re_all.start(),re_all.end()
    text_all = tw.wrap(f"{text[start:end-1]}{'' if text[end-2]=='[' else ', '}{', '.join(names)}]")
    with open(fname, 'w', encoding='utf8') as f: f.write(text[:start] + '\n'.join(text_all) + text[end:])

# Cell
def relative_import(name, fname):
    "Convert a module `name` to a name relative to `fname`"
    mods = name.split('.')
    splits = str(fname).split(os.path.sep)
    if mods[0] not in splits: return name
    i=len(splits)-1
    while i>0 and splits[i] != mods[0]: i-=1
    splits = splits[i:]
    while len(mods)>0 and splits[0] == mods[0]: splits,mods = splits[1:],mods[1:]
    return '.' * (len(splits)) + '.'.join(mods)

# Cell
_re_import = ReLibName(r'^(\s*)from (LIB_NAME\.\S*) import (.*)$')

# Cell
def _deal_import(code_lines, fname):
    def _replace(m):
        sp,mod,obj = m.groups()
        return f"{sp}from {relative_import(mod, fname)} import {obj}"
    return [_re_import.re.sub(_replace,line) for line in code_lines]

# Cell
_re_index_custom = re.compile(r'def custom_doc_links\(name\):(.*)$', re.DOTALL)

# Cell
def reset_nbdev_module():
    "Create a skeleton for <code>_nbdev</code>"
    fname = get_config().path("lib_path")/'_nbdev.py'
    fname.parent.mkdir(parents=True, exist_ok=True)
    sep = '\n' * (get_config().d.getint('cell_spacing', 1) + 1)
    if fname.is_file():
        with open(fname, 'r') as f: search = _re_index_custom.search(f.read())
    else: search = None
    prev_code = search.groups()[0] if search is not None else ' return None\n'
    with open(fname, 'w') as f:
        f.write(f"# AUTOGENERATED BY NBDEV! DO NOT EDIT!")
        f.write('\n\n__all__ = ["index", "modules", "custom_doc_links", "git_url"]')
        f.write('\n\nindex = {}')
        f.write('\n\nmodules = []')
        f.write(f'\n\ndoc_url = "{get_config().doc_host}{get_config().doc_baseurl}"')
        f.write(f'\n\ngit_url = "{get_config().git_url}"')
        f.write(f'{sep}def custom_doc_links(name):{prev_code}')

# Cell
class _EmptyModule():
    def __init__(self):
        self.index,self.modules = {},[]
        try: self.doc_url,self.git_url = f"{get_config().doc_host}{get_config().doc_baseurl}",get_config().git_url
        except FileNotFoundError: self.doc_url,self.git_url = '',''

    def custom_doc_links(self, name): return None

# Cell
def get_nbdev_module():
    "Reads <code>_nbdev</code>"
    try:
        spec = importlib.util.spec_from_file_location(f"{get_config().lib_name}._nbdev", get_config().path("lib_path")/'_nbdev.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except: return _EmptyModule()

# Cell
_re_index_idx = re.compile(r'index\s*=\s*{[^}]*}')
_re_index_mod = re.compile(r'modules\s*=\s*\[[^\]]*\]')

# Cell
def save_nbdev_module(mod):
    "Save `mod` inside <code>_nbdev</code>"
    fname = get_config().path("lib_path")/'_nbdev.py'
    with open(fname, 'r') as f: code = f.read()
    t = r',\n         '.join([f'"{k}": "{v}"' for k,v in mod.index.items()])
    code = _re_index_idx.sub("index = {"+ t +"}", code)
    t = r',\n           '.join(['"' + f.replace('\\','/') + '"' for f in mod.modules])
    code = _re_index_mod.sub(f"modules = [{t}]", code)
    with open(fname, 'w') as f: f.write(code)

# Cell
def split_flags_and_code(cell, return_type=list):
    "Splits the `source` of a cell into 2 parts and returns (flags, code)"
    source_str = cell['source'].replace('\r', '')
    code_lines = source_str.split('\n')
    split_pos = 0 if code_lines[0].strip().startswith('#') else -1
    for i, line in enumerate(code_lines):
        if not line.startswith('#') and line.strip() and not _re_from_future_import.match(line): break
    split_pos+=1
    res = code_lines[:split_pos], code_lines[split_pos:]
    if return_type is list: return res
    return tuple('\n'.join(r) for r in res)

# Cell
def create_mod_file(fname, nb_path, bare=False):
    "Create a module file for `fname`."
    try: bare = get_config().d.getboolean('bare', bare)
    except FileNotFoundError: pass
    fname.parent.mkdir(parents=True, exist_ok=True)
    try: dest = get_config().config_file.parent
    except FileNotFoundError: dest = nb_path
    file_path = os.path.relpath(nb_path, ).replace('\\', '/')
    with open(fname, 'w') as f:
        if not bare: f.write(f"# AUTOGENERATED! DO NOT EDIT! File to edit: {file_path} (unless otherwise specified).")
        f.write('\n\n__all__ = []')

# Cell
def create_mod_files(files, to_dict=False, bare=False):
    "Create mod files for default exports found in `files`"
    modules = []
    try: lib_path = get_config().path("lib_path")
    except FileNotFoundError: lib_path = Path()
    try: nbs_path = get_config().path("nbs_path")
    except FileNotFoundError: nbs_path = Path()
    for f in sorted(files):
        fname = Path(f)
        nb = read_nb(fname)
        default = find_default_export(nb['cells'])
        if default is not None:
            default = os.path.sep.join(default.split('.'))
            modules.append(default)
            if not to_dict: create_mod_file(lib_path/f'{default}.py', nbs_path/f'{fname}', bare=bare)
    return modules

# Cell
def _notebook2script(fname, modules, silent=False, to_dict=None, bare=False):
    "Finds cells starting with `#export` and puts them into a module created by `create_mod_files`"
    try: bare = get_config().d.getboolean('bare', bare)
    except FileNotFoundError: pass
    if os.environ.get('IN_TEST',0): return  # don't export if running tests
    try: spacing,has_setting = get_config().d.getint('cell_spacing', 1), True
    except FileNotFoundError: spacing,has_setting = 1, False
    sep = '\n' * (spacing + 1)
    try: lib_path = get_config().path("lib_path")
    except FileNotFoundError: lib_path = Path()
    fname = Path(fname)
    nb = read_nb(fname)
    default = find_default_export(nb['cells'])
    if default is not None:
        default = os.path.sep.join(default.split('.'))
    mod = get_nbdev_module()
    exports = [is_export(c, default) for c in nb['cells']]
    cells = [(i,c,e) for i,(c,e) in enumerate(zip(nb['cells'],exports)) if e is not None]
    for i,c,(e,a) in cells:
        if e not in modules: print(f'Warning: Exporting to "{e}.py" but this module is not part of this build')
        fname_out = lib_path/f'{e}.py'
        if bare: orig = "\n"
        else: orig = (f'# {"" if a else "Internal "}C' if e==default else f'# Comes from {fname.name}, c') + 'ell\n'
        flag_lines,code_lines = split_flags_and_code(c)
        if has_setting: code_lines = _deal_import(code_lines, fname_out)
        code = sep + orig + '\n'.join(code_lines)
        names = export_names(code)
        flags = '\n'.join(flag_lines)
        extra,code = extra_add(flags, code)
        code = _from_future_import(fname_out, flags, code, to_dict)
        if a:
            if to_dict is None: _add2all(fname_out, [f"'{f}'" for f in names if '.' not in f and len(f) > 0] + extra)
        mod.index.update({f: fname.name for f in names})
        code = re.sub(r' +$', '', code, flags=re.MULTILINE)
        if code != sep + orig[:-1]:
            if to_dict is not None: to_dict[e].append((i, fname, code))
            else:
                with open(fname_out, 'a', encoding='utf8') as f: f.write(code)
        if f'{e}.py' not in mod.modules: mod.modules.append(f'{e}.py')
    if has_setting: save_nbdev_module(mod)

    if not silent: print(f"Converted {fname.name}.")
    return to_dict

# Cell
def add_init(path):
    "Add `__init__.py` in all subdirs of `path` containing python files if it's not there already"
    for p,d,f in os.walk(path):
        for f_ in f:
            if f_.endswith('.py'):
                if not (Path(p)/'__init__.py').exists(): (Path(p)/'__init__.py').touch()
                break

# Cell
_re_version = re.compile('^__version__\s*=.*$', re.MULTILINE)

# Cell
def update_version():
    "Add or update `__version__` in the main `__init__.py` of the library"
    fname = get_config().path("lib_path")/'__init__.py'
    if not fname.exists(): fname.touch()
    version = f'__version__ = "{get_config().version}"'
    with open(fname, 'r') as f: code = f.read()
    if _re_version.search(code) is None: code = version + "\n" + code
    else: code = _re_version.sub(version, code)
    with open(fname, 'w') as f: f.write(code)

# Cell
_re_baseurl = re.compile('^baseurl\s*:.*$', re.MULTILINE)

# Cell
def update_baseurl():
    "Add or update `baseurl` in `_config.yml` for the docs"
    fname = get_config().path("doc_path")/'_config.yml'
    if not fname.exists(): return
    with open(fname, 'r') as f: code = f.read()
    if _re_baseurl.search(code) is None: code = code + f"\nbaseurl: {get_config().doc_baseurl}"
    else: code = _re_baseurl.sub(f"baseurl: {get_config().doc_baseurl}", code)
    with open(fname, 'w') as f: f.write(code)

# Cell
def nbglob(fname=None, recursive=None, extension='.ipynb', config_key='nbs_path') -> L:
    "Find all files in a directory matching an extension given a `config_key`."
    fname = Path(fname or get_config().path(config_key))
    if fname.is_file(): return [fname]
    if recursive == None: recursive=get_config().get('recursive', 'False').lower() == 'true'
    if fname.is_dir(): pat = f'**/*{extension}' if recursive else f'*{extension}'
    else: fname,_,pat = str(fname).rpartition(os.path.sep)
    if str(fname).endswith('**'): fname,pat = fname[:-2],'**/'+pat
    fls = L(Path(fname).glob(pat)).map(Path)
    return fls.filter(lambda x: x.name[0]!='_' and '/.' not in str(x))

# Cell
def notebook2script(fname=None, silent=False, to_dict=False, bare=False):
    "Convert notebooks matching `fname` to modules"
    # initial checks
    if os.environ.get('IN_TEST',0): return  # don't export if running tests
    if fname is None:
        reset_nbdev_module()
        update_version()
        update_baseurl()
    files = nbglob(fname=fname)
    d = collections.defaultdict(list) if to_dict else None
    modules = create_mod_files(files, to_dict, bare=bare)
    for f in sorted(files): d = _notebook2script(f, modules, silent=silent, to_dict=d, bare=bare)
    if to_dict: return d
    elif fname is None: add_init(get_config().path("lib_path"))

# Cell
class DocsTestClass:
    "for tests only"
    def test(): pass

# Internal Cell
#exporti
#for tests only
def update_lib_with_exporti_testfn(): pass