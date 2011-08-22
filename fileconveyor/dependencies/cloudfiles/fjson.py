from tokenize  import  generate_tokens, STRING, NAME, OP
from cStringIO import  StringIO
from re        import  compile, DOTALL

comments = compile(r'/\*.*\*/|//[^\r\n]*', DOTALL)

def _loads(string):
    '''
    Fairly competent json parser exploiting the python tokenizer and eval()

    _loads(serialized_json) -> object
    '''
    try:
        res = []
        consts = {'true': True, 'false': False, 'null': None}
        string = '(' + comments.sub('', string) + ')'
        for type, val, _, _, _ in generate_tokens(StringIO(string).readline):
            if (type == OP and val not in '[]{}:,()-') or \
               (type == NAME and val not in consts):
                raise AttributeError()
            elif type == STRING:
                res.append('u')
                res.append(val.replace('\\/', '/'))
            else:
                res.append(val)
        return eval(''.join(res), {}, consts)
    except:
        raise AttributeError()

# look for a real json parser first
try:
    # 2.6 will have a json module in the stdlib
    from json import loads as json_loads
except ImportError:
    try:
        # simplejson is popular and pretty good
        from simplejson import loads as json_loads
    # fall back on local parser otherwise
    except ImportError:
        json_loads = _loads

__all__ = ['json_loads']

