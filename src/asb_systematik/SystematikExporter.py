from injector import Injector, inject, singleton
from asb_systematik.SystematikDao import AlexandriaDbModule, SystematikDao,\
    SystematikTree
from xml.dom.minidom import getDOMImplementation

@singleton
class SystematikExporter(object):
    
    @inject
    def __init__(self, systematik_dao: SystematikDao):
        
        self.systematik_dao = systematik_dao
        
    def export(self, filename="/tmp/systematik.xml", flat=True):
        
        dom = self._start_dom()
        root_element = dom.documentElement
        
        tree = self.systematik_dao.fetch_tree(SystematikTree)
        if flat:
            dom = self._build_flat_xml(dom, tree)
        else:
            dom = self._build_tree_xml(dom, tree)
            
        file = open(filename, "w")
        file.write(dom.documentElement.toprettyxml())
        file.close()

    def _build_flat_xml(self, dom, tree):
        
        for node in tree.iterator:
            dom.documentElement.appendChild(self._create_node_element(dom, node))
        return dom

    def _build_tree_xml(self, dom, tree):
        
        root_node = tree.rootnode
        root_element = self._create_node_element(dom, root_node)
        for child_node in root_node.children:
            self._add_child(dom, root_element, child_node)
        dom.documentElement.appendChild(root_element)
        return dom
            
    def _add_child(self, dom, parent_element, node):
        
        element = self._create_node_element(dom, node)
        parent_element.appendChild(element)
        for child_node in node.children:
            self._add_child(dom, element, child_node)
        
        

    def _start_dom(self):
        
        impl = getDOMImplementation()

        return impl.createDocument(None, "ASB_Systematik", None)
    
    def _create_node_element(self, dom, node):
        
        element = dom.createElement("SystematikEintrag")
        if node.id is None:
            element.setAttribute("id", "0")
        else:
            element.setAttribute("id", "%s" % node.id)
        
        if node.parent is not None:
            if node.parent.id is None:
                element.setAttribute("parentid", "0")
            else:
                element.setAttribute("parentid", "%s" % node.parent.id)

        try:
            element.setAttribute("nextsiblingid", "%s" % node.next_sibling.id)
        except:
            pass
        try:
            element.setAttribute("previoussiblingid", "%s" % node.previous_sibling.id)
        except:
            pass
        
        element = self._append_text_element(dom, element, "Sigle", node.identifier)
        element = self._append_text_element(dom, element, "Beschreibung", node.beschreibung)
        element = self._append_text_element(dom, element, "Kommentar", node.kommentar)
        element = self._append_text_element(dom, element, "Entfernt", node.entfernt)
        element = self._append_laufzeit(dom, element, node)
        
        return element
    
    def _append_text_element(self, dom, element, tag, value):
        
        if value is None:
            return element
        string_value = "%s" % value
        if string_value.strip() == "":
            return element
        child_element = dom.createElement(tag)
        child_element.appendChild(dom.createTextNode(string_value))
        element.appendChild(child_element)
        return element
    
    def _append_laufzeit(self, dom, element, node):
        
        if node.startjahr is None:
            return element
        laufzeit_element = dom.createElement("Laufzeit")
        if node.endjahr is None:
            laufzeit_element.appendChild(dom.createTextNode("%s -" % node.startjahr))
        elif node.endjahr == node.startjahr:
            laufzeit_element.appendChild(dom.createTextNode("%s" % node.startjahr))
        else:
            laufzeit_element.appendChild(dom.createTextNode("%s - %s" % (node.startjahr, node.endjahr)))
        element.appendChild(laufzeit_element)
        return element
            
        

if __name__ == '__main__':
    injector = Injector([AlexandriaDbModule])
    exporter = injector.get(SystematikExporter)
    exporter.export(flat=False)