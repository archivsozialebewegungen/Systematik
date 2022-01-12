'''
Created on 15.07.2021

@author: michael
'''
from asb_systematik.SystematikDao import SystematikDao, SystematikTree,\
    SystematikNode
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from injector import singleton, inject

class NoSelectionException(Exception):
    
    pass

class SystematikQTreeWidgetItem(QTreeWidgetItem):
    """
    This is the GUI representation of a SystematikNode, all
    None values in the SystematikNode object need to be replaced
    by empty strings.
    """
    
    NODE_TYPES = ("Gliederungspunkt", "Physischer Bestand", "Digitaler Bestand")
    DIGITALISIERUNGS_STATUS = ("nicht digitalisiert", "teilweise digitalisiert", "vollständig digitalisiert")
    
    def __init__(self, parent, systematik_node: SystematikNode):
        
        self.systematik_node = systematik_node
        try:
            self.systematik_node.parent = parent.systematik_node
        except:
            # Happens on root nodes - parent then is no SystematikQTreeWidgetItem
            pass

        super().__init__(parent, ("%s" % systematik_node.identifier, self.display_text))
    
    def set_description(self, new_description):
        
        if new_description.strip() == "":
            self.systematik_node.beschreibung = None
        else:
            self.systematik_node.beschreibung = new_description
        self.setText(1, self.display_text)

    def get_description(self):
        
        if self.systematik_node.beschreibung is None:
            return ""
        else:
            return self.systematik_node.beschreibung

    def set_kommentar(self, new_comment):
        
        if new_comment.strip() == "":
            self.systematik_node.kommentar = None
        else:
            self.systematik_node.kommentar = new_comment
        self.setText(1, self.display_text)
        
    def get_kommentar(self):
        
        if self.systematik_node.kommentar is None:
            return ""
        else:
            return self.systematik_node.kommentar

    def set_entfernt(self, new_entfernt):
        
        if new_entfernt.strip() == "":
            self.systematik_node.entfernt = None
        else:
            self.systematik_node.entfernt = new_entfernt
        self.setText(1, self.display_text)

    def get_entfernt(self):
        
        if self.systematik_node.entfernt is None:
            return ""
        else:
            return self.systematik_node.entfernt

    def set_startjahr(self, new_startjahr):
        
        self.systematik_node.startjahr = new_startjahr
        self.setText(1, self.display_text)

    def get_startjahr(self):
        
        return self.systematik_node.startjahr

    def set_endjahr(self, new_endjahr):
        
        self.systematik_node.endjahr = new_endjahr
        self.setText(1, self.display_text)

    def get_endjahr(self):
        
        return self.systematik_node.endjahr

    def _get_display_text(self):

        if self.systematik_node.beschreibung is None:
            desc = "Keine Beschreibung!"
        else:
            desc = self.systematik_node.beschreibung

        if self.systematik_node.kommentar is not None:
            desc = "* %s" % desc
            
        if self.systematik_node.startjahr is not None or self.systematik_node.endjahr is not None:
            if self.systematik_node.startjahr is None:
                desc = "%s (bis %d)" % (desc, self.systematik_node.endjahr)
            elif self.systematik_node.endjahr is None:
                desc = "%s (ab %d)" % (desc, self.systematik_node.startjahr)
            else:
                desc = "%s (%d - %d)" % (desc, self.systematik_node.startjahr, self.systematik_node.endjahr)
                
        return desc

    beschreibung = property(get_description, set_description)        
    kommentar = property(get_kommentar, set_kommentar)        
    entfernt = property(get_entfernt, set_entfernt)        
    startjahr = property(get_startjahr, set_startjahr)        
    endjahr = property(get_endjahr, set_endjahr)        
    display_text = property(_get_display_text)

class SystematikQTreeWidget(QTreeWidget):
    
    def filter(self, itemfilter):
        
        assert(itemfilter == itemfilter.upper())
        
        for index in range(0, self.topLevelItemCount()):
            self._evaluate_filter(self.topLevelItem(index), itemfilter)
            
    def _evaluate_filter(self, item, itemfilter):
        if itemfilter == "":
            is_visible = True
        else:
            is_visible = item.systematik_node.is_visible(itemfilter)
        item.setHidden(not is_visible)
        if is_visible:
            for index in range(0, item.childCount()):
                self._evaluate_filter(item.child(index), itemfilter)

    def expand_all(self):
        
        for index in range(0, self.topLevelItemCount()):
            self.expand(self.topLevelItem(index))
            
    def expand_selected(self):
        
        selected_items = self.selectedItems()
        if len(selected_items) == 0:
            self.expand_all()
        else:
            for item in selected_items:
                self.expand(item)

    def expand(self, item: SystematikQTreeWidgetItem):
        
        item.setExpanded(True)
        for index in range(0, item.childCount()):
            self.expand(item.child(index))
        
    def collapse_all(self):
        
        for index in range(0, self.topLevelItemCount()):
            self.collapse(self.topLevelItem(index))
            
    def collapse_selected(self):
        
        selected_items = self.selectedItems()
        if len(selected_items) == 0:
            self.collapse_all()
        else:
            for item in selected_items:
                self.collapse(item)

    def collapse(self, item: SystematikQTreeWidgetItem):
        
        item.setExpanded(False)
        for index in range(0, item.childCount()):
            self.collapse(item.child(index))
            
    def first_selected(self):

        selected_items = self.selectedItems()

        if len(selected_items) == 0:
            raise NoSelectionException("No item selected")
        
        return selected_items[0]
        
@singleton
class SystematikTreeWidgetService:
    
    
    @inject
    def __init__(self, systematik_dao: SystematikDao):
        
        self.dao = systematik_dao
        self._tree = None
        
    def create_tree_widget(self):

        tree_widget = SystematikQTreeWidget()
        tree_widget.setColumnCount(2)
        tree_widget.setColumnWidth(0,240)
        tree_widget.setHeaderLabels(("Systematikpunkt", "Beschreibung"))

        root_widget_items = []
        for root_node in self.tree.rootnode.children:
            root_widget_item = (SystematikQTreeWidgetItem(tree_widget, root_node))
            self._add_child_items(tree_widget, root_widget_item)
            root_widget_items.append(root_widget_item)
        tree_widget.insertTopLevelItems(0, root_widget_items)
        return tree_widget
    
    def _add_child_items(self, tree_widget, parent: SystematikQTreeWidgetItem):
        
        for child in parent.systematik_node.children:
            widget_item = SystematikQTreeWidgetItem(parent, child)
            self._add_child_items(tree_widget, widget_item)

    def _get_tree(self):
        
        if self._tree is None:
            self._tree = self.dao.fetch_tree(SystematikTree)
        return self._tree
    
    def is_used(self, item_widget: SystematikQTreeWidget):
        
        return self.dao.is_used(item_widget.systematik_node.identifier)
    
    def first_usage(self, item_widget: SystematikQTreeWidget):
        
        return self.dao.get_first_usage(item_widget.systematik_node.identifier)

    def save(self, item_widget: SystematikQTreeWidget):
        
        if self.dao.exists(item_widget.systematik_node.identifier):
            self.dao.update_node(item_widget.systematik_node)
        else:
            self.dao.insert_node(item_widget.systematik_node)
            new_node = item_widget.systematik_node
            parent = new_node.parent
            if len(parent.children) != 0:
                previous_sibling = parent.children[-1]
                new_node.previous_sibling = previous_sibling
                previous_sibling.next_sibling = new_node
            item_widget.systematik_node.parent.children.append(item_widget.systematik_node)
        self._tree = None
        
    def delete(self, item_widget: SystematikQTreeWidget):

        if item_widget.systematik_node.previous_sibling != None:
            item_widget.systematik_node.previous_sibling.next_sibling = None
        item_widget.systematik_node.parent.children.remove(item_widget.systematik_node)
        self.dao.delete_node(item_widget.systematik_node)
        self._tree = None
    
    tree = property(_get_tree)
