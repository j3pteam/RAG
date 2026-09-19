from html.parser import HTMLParser
VOID={"area","base","br","col","embed","hr","img","input","link","meta",
      "param","source","track","wbr"}
class Check(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.stack=[]; self.errors=[]
    def handle_starttag(self,tag,attrs):
        if tag not in VOID: self.stack.append((tag,self.getpos()[0]))
    def handle_endtag(self,tag):
        if tag in VOID: return
        if not self.stack:
            self.errors.append(f"line {self.getpos()[0]}: </{tag}> with nothing open"); return
        if self.stack[-1][0]!=tag:
            self.errors.append(f"line {self.getpos()[0]}: </{tag}> closes <{self.stack[-1][0]}> opened at line {self.stack[-1][1]}")
            for i in range(len(self.stack)-1,-1,-1):
                if self.stack[i][0]==tag: del self.stack[i:]; return
            return
        self.stack.pop()
import sys
html=open(sys.argv[1],encoding="utf-8").read()
c=Check(); c.feed(html)
for t,l in c.stack: c.errors.append(f"<{t}> opened at line {l} never closed")
if c.errors:
    print(f"{len(c.errors)} problem(s):"); [print("  ",e) for e in c.errors[:12]]; sys.exit(1)
print("HTML tags balance")
