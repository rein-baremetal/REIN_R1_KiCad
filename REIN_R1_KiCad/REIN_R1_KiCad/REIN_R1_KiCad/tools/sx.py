import re
def parse(s):
    tok=re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')
    stack=[[]]
    for m in tok.finditer(s):
        t=m.group(0)
        if t=='(':
            stack.append([])
        elif t==')':
            x=stack.pop(); stack[-1].append(x)
        else:
            stack[-1].append(t)
    return stack[0][0]
def q(t): return t[1:-1] if isinstance(t,str) and t.startswith('"') else t
def find(n,name): return [c for c in n if isinstance(c,list) and c and c[0]==name]
