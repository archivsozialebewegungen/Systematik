from injector import Injector, inject, singleton
from asb_systematik.SystematikDao import AlexandriaDbModule, SystematikDao,\
    SystematikTree, SystematikIdentifier
from datetime import date
import os
import xmlschema
from xml.dom.minidom import getDOMImplementation
from enum import StrEnum

class EAD_TYPE(StrEnum):
    
    TEKTONIK = "Tektonik"
    FINDBUCH = "Findbuch"
    
    def as_id(self):
        
        return "ASB_" + self
    
    def bestands_type(self):
        
        if self == EAD_TYPE.TEKTONIK:
            return "file"
        else:
            return "collection"
@singleton
class SystematikExporter(object):
    
    @inject
    def __init__(self, systematik_dao: SystematikDao):
        
        tektonik_schema_file = os.path.join(os.path.dirname(__file__), "..", "data", "EAD_DDB_1.2_Tektonik_XSD1.1.xsd")
        self.tektonik_schema = xmlschema.XMLSchema11(tektonik_schema_file)
        findbuch_schema_file = os.path.join(os.path.dirname(__file__), "..", "data", "EAD_DDB_1.2_Findbuch_XSD1.1.xsd")
        self.findbuch_schema = xmlschema.XMLSchema11(findbuch_schema_file)
        self.systematik_dao = systematik_dao

        self.systematik_tree = self.systematik_dao.fetch_tree(SystematikTree)
        
    def full_export(self, basedir=os.path.join("/", "tmp")):
        
        self.ead_export(os.path.join(basedir, "asb_systematik_tektonik.xml"), EAD_TYPE.TEKTONIK)
        for syst_punkt in range(0, 23):
            if syst_punkt == 18:
                continue
            self.ead_export(os.path.join(basedir, "asb_systematik_findbuch_%02d.xml") % syst_punkt, EAD_TYPE.FINDBUCH, syst_punkt)
        
    def ead_export(self, filename: str = "/tmp/systematik.xml", ead_type:EAD_TYPE = EAD_TYPE.TEKTONIK, syst_punkt:int = 0):
        
        dom = self._init_ead_dom()
        
        dom = self._build_xml(dom, ead_type, syst_punkt)
            
        file = open(filename, "w")
        file.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        file.write(dom.documentElement.toprettyxml(indent="  ", standalone=True))
        file.close()

        if ead_type == EAD_TYPE.TEKTONIK:
            xmlschema.validate(filename, self.tektonik_schema)
        else:
            xmlschema.validate(filename, self.findbuch_schema)

    def _build_xml(self, dom, ead_type: EAD_TYPE, syst_punkt: int):
        
        archdesc_element = self._add_element(dom, dom.documentElement, "archdesc")
        archdesc_element.setAttribute("level", "collection")
        archdesc_element.setAttribute("type", "%s" % ead_type)
        
        did_element = self._add_element(dom, archdesc_element, "did")
        
        repository_element = self._add_element(dom, did_element, "repository")
        repository_element.setAttribute("label", "Baden-Württemberg")

        self._add_element(dom, repository_element, "corpname", "Archiv Soziale Bewegungen e.V.")
        address_element = self._add_element(dom, repository_element, "address")
        self._add_element(dom, address_element, "addressline", "Adlerstr.12")
        self._add_element(dom, address_element, "addressline", "D-79098 Freiburg")
        self._add_element(dom, address_element, "addressline", "info@archivsozialebewegungen.de")
        
        dsc_element = self._add_element(dom, archdesc_element, "dsc")
        
        if ead_type == EAD_TYPE.TEKTONIK:
            self._add_tektonik(dom, dsc_element)
        else:
            self._add_findbuch(dom, dsc_element, syst_punkt)
        
        return dom

    def _add_tektonik(self, dom, dsc_element):
        
        
        main_c_element = self._add_element(dom, dsc_element, "c")
        main_c_element.setAttribute("level", "collection")
        main_c_element.setAttribute("id", EAD_TYPE.TEKTONIK.as_id())
        
        main_did_element = self._add_element(dom, main_c_element, "did")
        main_repository_element = self._add_element(dom, main_did_element, "repository")
        main_corpname_element = self._add_element(dom, main_repository_element, "corpname", "Archiv Soziale Bewegungen e.V.")
        main_corpname_element.setAttribute("role", "Archive der Hochschulen sowie wissenschaftlicher Institutionen")
        main_corpname_element.setAttribute("id", "DE-Frei220")
        self._add_element(dom, main_did_element, "unittitle", "Archiv Soziale Bewegungen e.V. (Archivtektonik)")

        for child_node in self.systematik_tree.rootnode.children:
            if child_node.identifier.punkt in ("18", "23"):
                continue
            element = self._create_ead_node_element(dom, child_node, EAD_TYPE.TEKTONIK)
            main_c_element.appendChild(element)
        
    def _add_findbuch(self, dom, dsc_element, syst_punkt):

        findbuch_root = self.systematik_tree.find_node(SystematikIdentifier("%s" % syst_punkt))
        
        self._add_ead_child(dom, dsc_element, findbuch_root, EAD_TYPE.FINDBUCH)

    def _add_ead_child(self, dom, parent_element, node, ead_type):
        
        element = self._create_ead_node_element(dom, node, ead_type)
        parent_element.appendChild(element)
        for child_node in node.children:
            self._add_ead_child(dom, element, child_node, ead_type)
            
    def _init_ead_dom(self):
        
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
        header_element.setAttribute("countryencoding", "iso3166-1")
        header_element.setAttribute("dateencoding", "iso8601")
        header_element.setAttribute("langencoding", "iso639-2b")
        header_element.setAttribute("repositoryencoding", "iso15511"),
        header_element.setAttribute("scriptencoding", "iso15924")

        id_element = dom.createElement("eadid")
        header_element.appendChild(id_element)
        id_element.setAttribute("mainagencycode", "DE-Frei202")
        id_element.setAttribute("url", "http://archivsozialebewegungen.de")
        id_text = dom.createTextNode("ASB-Systematik")
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
        date_element.setAttribute("normal", today.strftime("%Y-%m-%d"))
        date_text = dom.createTextNode(today.strftime("%d.%m.%Y"))
        date_element.appendChild(date_text)
        
        return dom
    
    def _create_ead_node_element(self, dom, node, ead_type:EAD_TYPE):
        
        element = dom.createElement("c")
        element.setAttribute("id", "ASB-%s" % node.id)
        
        if len(node.children) == 0:
            element.setAttribute("level", "file")
        elif node.parent is None:
            raise Exception("This should not happen")
        elif node.parent.id is None:
            element.setAttribute("level", ead_type.bestands_type())
        else:
            element.setAttribute("level", "class")
 
        did_element = self._add_element(dom, element, "did")
        self._add_element(dom, did_element, "unitid", node.identifier)
        self._add_element(dom, did_element, "unittitle", node.beschreibung)
        if node.startjahr is not None:
            self._append_ead_laufzeit(dom, did_element, node)
        if node.kommentar is not None:
            note_element = self._add_element(dom, did_element, "note")
            self._add_element(dom, note_element, "p", node.kommentar)
 
        if node.entfernt is not None:
            odd_element = self._add_element(dom, element, "odd")
            element.appendChild(odd_element)
            self._add_element(dom, odd_element, "head", "Entfernte Materialien:")
            self._add_element(dom, odd_element, "p", node.entfernt)
       
        return element

    def _add_element(self, dom, element, tag, value=None):

        child_element = dom.createElement(tag)
        element.appendChild(child_element)
        
        if value is not None:
            child_element.appendChild(dom.createTextNode("%s" % value))

        return child_element
    
    def _append_ead_laufzeit(self, dom, element, node):
        
        if node.startjahr is None:
            return element
        laufzeit_element = dom.createElement("unitdate")
        element.appendChild(laufzeit_element)

        if node.endjahr is None:
            laufzeit_element.appendChild(dom.createTextNode("%s -" % node.startjahr))
            laufzeit_element.setAttribute("normal", "%s-01-01/2999-12-31" % node.startjahr)
        elif node.endjahr == node.startjahr:
            laufzeit_element.appendChild(dom.createTextNode("%s" % node.startjahr))
            laufzeit_element.setAttribute("normal", "%s-01-01/%s-12-31" % (node.startjahr, node.startjahr))
        else:
            laufzeit_element.appendChild(dom.createTextNode("%s - %s" % (node.startjahr, node.endjahr)))
            laufzeit_element.setAttribute("normal", "%s-01-01/%s-12-31" % (node.startjahr, node.endjahr))
        
        return element

if __name__ == '__main__':
    injector = Injector([AlexandriaDbModule])
    exporter = injector.get(SystematikExporter)
    exporter.full_export()
