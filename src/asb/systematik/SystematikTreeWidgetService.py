'''
Created on 15.07.2021

@author: michael
'''
from asb.systematik.SystematikDao import SystematikDao, SystematikTree,\
    SystematikNode
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem
from injector import singleton, inject

class NoSelectionException(Exception):
    
    pass

class SystematikQTreeWidgetItem(QTreeWidgetItem):
    
    def __init__(self, parent, systematik_node: SystematikNode):
        
        if systematik_node.db_kommentar is not None:
            beschreibung = "* %s" % systematik_node.beschreibung
        else:
            beschreibung = systematik_node.beschreibung
        
        super().__init__(parent, ("%s" % systematik_node.identifier, beschreibung))
        self.systematik_node = systematik_node
        
    def alter_description(self, new_description):
        
        self.systematik_node.beschreibung = new_description
        self.setText(1, self.beschreibung_display)

    def alter_kommentar(self, new_comment):
        
        self.systematik_node.kommentar = new_comment
        self.setText(1, self.beschreibung_display)
        
    def _get_beschreibung_display(self):

        if self.systematik_node.db_kommentar is not None:
            return "* %s" % self.systematik_node.beschreibung
        else:
            return self.systematik_node.beschreibung
        
    beschreibung_display = property(_get_beschreibung_display)

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
    
    def save(self, item_widget: SystematikQTreeWidget):
        
        if self.dao.exists(item_widget.systematik_node.identifier):
            self.dao.update_node(item_widget.systematik_node)
        else:
            self.dao.insert_node(item_widget.systematik_node)
        self._tree = None
        
    def delete(self, item_widget: SystematikQTreeWidget):

        self.dao.delete_node(item_widget.systematik_node)
        self._tree = None
    
    tree = property(_get_tree)