"""Bounded interpreter for a documented Python-shaped decision language.

This is not Python eval/exec, a Python VM, or a general Python sandbox. Only
explicit AST operations below exist. No host objects or functions enter scope.
"""
import ast
import math
import operator

VERSION = 'restricted-python-1'
MAX_STEPS = 12000


class ProgramError(ValueError):
    pass


class Returned(Exception):
    def __init__(self, value):
        self.value = value


ALLOWED = (ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Assign, ast.Name,
           ast.Load, ast.Store, ast.Constant, ast.List, ast.Dict, ast.Subscript,
           ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
           ast.UnaryOp, ast.USub, ast.UAdd, ast.Not, ast.BoolOp, ast.And, ast.Or,
           ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
           ast.Is, ast.IsNot, ast.If, ast.For, ast.Return, ast.Call, ast.IfExp,
           ast.Break, ast.Continue, ast.Pass)
FUNCTIONS = {'len', 'min', 'max', 'abs', 'append'}


def parse_program(source):
    if not isinstance(source, str) or not 1 <= len(source.encode()) <= 6000:
        raise ProgramError('Source must contain 1–6000 UTF-8 bytes')
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise ProgramError('Invalid decision function syntax') from exc
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ProgramError('Provide exactly one def decide(request) function')
    func = tree.body[0]
    args = func.args
    if (func.name != 'decide' or func.decorator_list or func.returns or func.type_comment
            or getattr(func, 'type_params', []) or args.posonlyargs or args.vararg
            or args.kwarg or args.kwonlyargs or args.defaults or args.kw_defaults
            or len(args.args) != 1 or args.args[0].arg != 'request' or args.args[0].annotation):
        raise ProgramError('Use def decide(request) without decorators or annotations')
    nodes = list(ast.walk(tree))
    if len(nodes) > 1500:
        raise ProgramError('Program is too complex')
    for node in nodes:
        if type(node) not in ALLOWED or (isinstance(node, ast.FunctionDef) and node is not func):
            raise ProgramError(f'Unsupported syntax: {type(node).__name__}')
        if isinstance(node, ast.Name) and node.id.startswith('_'):
            raise ProgramError('Private names are not supported')
        if isinstance(node, ast.Assign) and (len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name)):
            raise ProgramError('Assign only to local variable names')
        if isinstance(node, ast.For) and (not isinstance(node.target, ast.Name) or node.orelse):
            raise ProgramError('Use for name in list without else')
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name)
                or node.func.id not in FUNCTIONS or node.keywords):
            raise ProgramError('Allowed functions: len, min, max, abs, append')
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, float, str, bool, type(None))
                or isinstance(node.value, (int,float)) and abs(node.value) > 10**12):
            raise ProgramError('Unsupported or oversized constant')
        if isinstance(node, ast.Dict) and any(key is None for key in node.keys):
            raise ProgramError('Dictionary unpacking is not supported')
    return func.body


class Interpreter:
    def __init__(self, request):
        self.env = {'request': request}
        self.steps = MAX_STEPS
        self.line = 1

    def tick(self):
        self.steps -= 1
        if self.steps < 0:
            raise ProgramError('Decision step limit exceeded')

    def number(self, value):
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 10**12:
            raise ProgramError('Expected finite number in range ±1e12')
        return value

    def expr(self, node):
        self.line = getattr(node, 'lineno', self.line)
        self.tick()
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.env[node.id]
        if isinstance(node, ast.List):
            return [self.expr(item) for item in node.elts]
        if isinstance(node, ast.Dict):
            result = {}
            for key, value in zip(node.keys, node.values):
                key = self.expr(key)
                if type(key) is not str:
                    raise ProgramError('Dictionary keys must be strings')
                result[key] = self.expr(value)
            return result
        if isinstance(node, ast.Subscript):
            value, key = self.expr(node.value), self.expr(node.slice)
            if not ((type(value) is dict and type(key) is str) or (type(value) is list and type(key) is int)):
                raise ProgramError('Index a list with an integer or a dictionary with a string')
            return value[key]
        if isinstance(node, ast.BinOp):
            a, b = self.number(self.expr(node.left)), self.number(self.expr(node.right))
            operation = {ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
                         ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}[type(node.op)]
            return self.number(operation(a,b))
        if isinstance(node, ast.UnaryOp):
            value = self.expr(node.operand)
            if isinstance(node.op, ast.Not):
                return not value
            return -self.number(value) if isinstance(node.op, ast.USub) else self.number(value)
        if isinstance(node, ast.BoolOp):
            for item in node.values:
                value = self.expr(item)
                if isinstance(node.op, ast.And) and not value or isinstance(node.op, ast.Or) and value:
                    return value
            return value
        if isinstance(node, ast.Compare):
            a = self.expr(node.left)
            for op, item in zip(node.ops, node.comparators):
                b = self.expr(item)
                if type(a) in (dict,list) or type(b) in (dict,list):
                    raise ProgramError('Compare scalar values only')
                operation = {ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Lt:operator.lt,
                             ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge,
                             ast.Is:operator.is_,ast.IsNot:operator.is_not}[type(op)]
                if not operation(a,b):
                    return False
                a = b
            return True
        if isinstance(node, ast.IfExp):
            return self.expr(node.body if self.expr(node.test) else node.orelse)
        if isinstance(node, ast.Call):
            values = [self.expr(arg) for arg in node.args]
            name = node.func.id
            if name == 'len' and len(values)==1 and type(values[0]) in (dict,list,str):
                return len(values[0])
            if name == 'append' and len(values)==2 and type(values[0]) is list and len(values[0])<128:
                return values[0] + [values[1]]
            if name == 'abs' and len(values)==1:
                return abs(self.number(values[0]))
            if name in ('min','max') and 1 <= len(values) <= 16:
                return (min if name=='min' else max)([self.number(v) for v in values])
            raise ProgramError('Invalid function arguments or list limit exceeded')
        raise ProgramError('Unsupported expression')

    def block(self, nodes):
        for node in nodes:
            self.line = getattr(node, 'lineno', self.line)
            self.tick()
            if isinstance(node, ast.Assign):
                self.env[node.targets[0].id] = self.expr(node.value)
            elif isinstance(node, ast.If):
                signal = self.block(node.body if self.expr(node.test) else node.orelse)
                if signal:
                    return signal
            elif isinstance(node, ast.For):
                items = self.expr(node.iter)
                if type(items) is not list or len(items)>256:
                    raise ProgramError('Loop over a list of at most 256 items')
                for item in items:
                    self.tick()
                    self.env[node.target.id] = item
                    if self.block(node.body) == 'break':
                        break
            elif isinstance(node, ast.Return):
                raise Returned(self.expr(node.value) if node.value else None)
            elif isinstance(node, ast.Break):
                return 'break'
            elif isinstance(node, ast.Continue):
                return 'continue'
            elif not isinstance(node, ast.Pass):
                raise ProgramError('Unsupported statement')

    def check_output(self, value, depth=0):
        self.tick()
        if depth>16:
            raise ProgramError('Output nesting limit exceeded')
        if type(value) in (list,dict):
            for item in (value.values() if type(value) is dict else value):
                self.check_output(item,depth+1)
        elif type(value) not in (int,float,str,bool,type(None)):
            raise ProgramError('Invalid output')


def program_bot(source):
    body = parse_program(source)
    def decide(request):
        runtime = Interpreter(request)
        try:
            try:
                runtime.block(body)
            except Returned as result:
                runtime.check_output(result.value)
                return result.value
            raise ProgramError('Decision must return an action envelope')
        except (ProgramError, KeyError, IndexError, TypeError, ZeroDivisionError, RecursionError) as exc:
            details = {KeyError:'Unknown variable or dictionary key', IndexError:'List index out of range',
                       TypeError:'Invalid value types', ZeroDivisionError:'Division by zero',
                       RecursionError:'Expression nesting limit exceeded'}
            message = str(exc) if isinstance(exc, ProgramError) else details[type(exc)]
            raise ProgramError(f'Line {runtime.line}: {message}') from None
    return decide
