'''
Created on 27.07.2021

@author: michael
'''
from asb.systematik.SystematikDao import SystematikTree, SystematikDao, roemisch,\
    SystematikDbModule
import datetime
import locale
from injector import Injector

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

def tex_sanitizing(text: str) -> str:
    
    text = text.replace("&", "\\&")
    text = text.replace('(?<=\s)"', ",,")
    text = text.replace('"', "``")
    return text

class SystematikTexTree(SystematikTree):


    def __init__(self, node_hash):
        
        super().__init__(node_hash)
        
        self.itemlist_open = False
        self.descriptionlist_open = False
        
    def get_prefix(self):
        
        return """\\documentclass[twoside,ngerman]{article}
\\usepackage[T1]{fontenc}
\\usepackage[utf8]{inputenc}
\\usepackage{geometry}
\\geometry{verbose,tmargin=2cm,bmargin=2cm,lmargin=2cm,rmargin=2cm}\\usepackage{scrpage2}
\\pagestyle{scrheadings}
\\clearscrheadfoot
\\setlength{\\parindent}{0bp}
\\usepackage{babel}
\\begin{document}
\\raggedbottom{}
\\sloppy{}
\\ohead{\\pagemark}
"""
    
    def get_postfix(self):

        tex = "\n"        
        if self.itemlist_open:
            tex +=  "\\end{itemize}\n"
        if self.descriptionlist_open:
            tex += "\n\\end{description}\n"
        tex += "\\end{document}"
        
        return tex

    def _get_string(self, node):
        
        string = ""

        if not node.is_sub() and self.itemlist_open:
            string += "\n\\end{itemize}\n"
            self.itemlist_open = False
            
        if not node.is_roman() and self.descriptionlist_open:
            string += "\n\\end{description}\n"
            self.descriptionlist_open = False

        if node.is_sub():
            if not self.itemlist_open:
                string += "\n\\begin{itemize}\n"
                self.itemlist_open = True
            string += "\\item %s\n\n" % tex_sanitizing(node.beschreibung)
        
        elif node.is_roman():
            if not self.descriptionlist_open:
                string += "\n\\begin{description}\n"
                self.descriptionlist_open = True
            string += "\\item[{%s}:] %s\n\n" % (roemisch[node.identifier.roemisch], tex_sanitizing(node.beschreibung))
        
        else:
            depth = node.get_depth()
            if depth == 0:
                string += """\\title{%s}
\\date{%s}
\\maketitle
""" % (tex_sanitizing(node.beschreibung), datetime.date.today().strftime("%d. %B %Y"))
            elif depth == 1:
                string += "\pagebreak{}\part*{%s: %s}\n\setcounter{page}{1}\n\ihead{%s: %s}\n" % (node.identifier, tex_sanitizing(node.beschreibung), node.identifier, tex_sanitizing(node.beschreibung))
            elif depth == 2:
                string += "\section*{%s: %s}\n" % (node.identifier, tex_sanitizing(node.beschreibung))
            elif depth == 3:
                string += "\subsection*{%s: %s}\n" % (node.identifier, tex_sanitizing(node.beschreibung))
            elif depth == 4:
                string += "\subsubsection*{%s: %s}\n" % (node.identifier, tex_sanitizing(node.beschreibung))
            elif depth == 5:
                string += "\paragraph*{%s: %s}\n" % (node.identifier, tex_sanitizing(node.beschreibung))
            else:
                string += "\subparagraph*{%s: %s}\n" % (node.identifier, tex_sanitizing(node.beschreibung))
            
        for child in node.children:
            string += self._get_string(child)
        return string
    
    def __str__(self):
        
        return self.get_prefix() + self._get_string(self.rootnode) + self.get_postfix()


if __name__ == '__main__':
 
    injector = Injector([SystematikDbModule])
    dao = injector.get(SystematikDao)
    tree = dao.fetch_tree(SystematikTexTree)
    tex_file = open("/tmp/systematik.tex", "w")
    tex_file.write("%s" % tree)
    tex_file.close()
