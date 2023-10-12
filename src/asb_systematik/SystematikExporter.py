from injector import Injector, inject, singleton
from asb_systematik.SystematikDao import AlexandriaDbModule, SystematikDao,\
    SystematikTree
from xml.dom.minidom import getDOMImplementation
from datetime import date
import os
import xmlschema

@singleton
class SystematikExporter(object):
    
    @inject
    def __init__(self, systematik_dao: SystematikDao):
        
        self.schema = os.path.join(os.path.dirname(__file__), "..", "data", "EAD_DDB_1.2_Tektonik_XSD1.0.xsd")
        self.systematik_dao = systematik_dao
        
    def ead_export(self, filename="/tmp/systematik.xml", flat=True):
        
        dom = self._ead_dom()
        
        tree = self.systematik_dao.fetch_tree(SystematikTree)
        
        dom = self._build_ead_tree_xml(dom, tree)
            
        file = open(filename, "w")
        file.write(dom.documentElement.toprettyxml(indent="  ", standalone=True))
        file.close()
        
        xmlschema.validate(filename, self.schema)

    def _build_ead_tree_xml(self, dom, tree):
        
        root_node = tree.rootnode
        
        archdesc_element = dom.createElement("archdesc")
        archdesc_element.setAttribute("level", "collection")
        archdesc_element.setAttribute("type", "Tektonik")
        dom.documentElement.appendChild(archdesc_element)
        
        did_element = dom.createElement("did")
        archdesc_element.appendChild(did_element)
        
        repository_element = dom.createElement("repository")
        did_element.appendChild(repository_element)
        repository_element.setAttribute("label", "ASB")
        
        dsc_element = dom.createElement("dsc")
        archdesc_element.appendChild(dsc_element)
        
        for child_node in root_node.children:
            self._add_ead_child(dom, dsc_element, child_node)
        
        return dom

    def _add_ead_child(self, dom, parent_element, node):
        
        element = self._create_ead_node_element(dom, node)
        parent_element.appendChild(element)
        for child_node in node.children:
            self._add_ead_child(dom, element, child_node)
        
    def _ead_dom(self):
        
        impl = getDOMImplementation()

        dom = impl.createDocument(None, "ead", None)
        
        root = dom.documentElement
        root.setAttribute("xmlns", "urn:isbn:1-931666-22-9")
        root.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink")
        root.setAttribute("xsi:schemaLocation", "urn:isbn:1-931666-22-9 http://www.loc.gov/ead/ead.xsd")
        root.setAttribute("audience", "external")
        
        header_element = dom.createElement("eadheader")
        root.appendChild(header_element)

        id_element = dom.createElement("eadid")
        header_element.appendChild(id_element)
        id_text = dom.createTextNode("BW-Frei202")
        id_element.appendChild(id_text)
        
        filedesc_element = dom.createElement("filedesc")
        header_element.appendChild(filedesc_element)
        titlestmt_element = dom.createElement("titlestmt")
        filedesc_element.appendChild(titlestmt_element)
        titleproper_element = dom.createElement("titleproper")
        titlestmt_element.appendChild(titleproper_element)
        title_text = dom.createTextNode("Archiv Soziale Bewegungen e.V. (Archivtektonik)")
        titleproper_element.appendChild(title_text)
        
        profiledesc_element = dom.createElement("profiledesc")
        header_element.appendChild(profiledesc_element)
        creation_element = dom.createElement("creation")
        profiledesc_element.appendChild(creation_element)
        date_element = dom.createElement("date")
        creation_element.appendChild(date_element)
        today = date.today()
        # Does not validate correctly
        #date_element.setAttribute("normal", today.strftime("%Y.%m.%d"))
        date_text = dom.createTextNode(today.strftime("%d.%m.%Y"))
        date_element.appendChild(date_text)
        
        return dom
    
    def _create_ead_node_element(self, dom, node):
        
        element = dom.createElement("c")
        element.setAttribute("id", "Tekt_f4ccea23-184e-4ced-ab29-%s" % node.id)
        
        if len(node.children) == 0:
            element.setAttribute("level", "file")
        elif node.parent is None:
            raise Exception("This should not happen")
        elif node.parent.id is None:
            element.setAttribute("level", "class")
        else:
            element.setAttribute("level", "class")

        did_element = dom.createElement("did")
        element.appendChild(did_element)
        did_element = self._append_text_element(dom, did_element, "unitid", node.identifier)
        did_element = self._append_text_element(dom, did_element, "unittitle", node.beschreibung)
        #if node.kommentar is not None:
        #    did_element = self._append_text_element(dom, did_element, "note", node.kommentar)
        #if node.entfernt is not None:
        #    did_element = self._append_text_element(dom, element, "odd", node.entfernt)
        #did_element = self._append_ead_laufzeit(dom, element, node)
        
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
    
    def _append_ead_laufzeit(self, dom, element, node):
        
        if node.startjahr is None:
            return element
        laufzeit_element = dom.createElement("unitdate")
        element.appendChild(laufzeit_element)

        if node.endjahr is None:
            laufzeit_element.appendChild(dom.createTextNode("%s -" % node.startjahr))
        elif node.endjahr == node.startjahr:
            laufzeit_element.appendChild(dom.createTextNode("%s" % node.startjahr))
        else:
            laufzeit_element.appendChild(dom.createTextNode("%s - %s" % (node.startjahr, node.endjahr)))
        # TODO: normal attribute
        
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
    exporter.ead_export("/tmp/systematik_ead.xml")
