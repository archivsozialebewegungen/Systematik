import sys

from PyQt5.QtWidgets import QWidget, QApplication, QGroupBox, \
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QLineEdit,\
    QDialog, QDialogButtonBox, QMessageBox, QRadioButton,\
    QPlainTextEdit, QCheckBox
from injector import Injector, inject
from asb_systematik.SystematikTreeWidgetService import SystematikTreeWidgetService,\
    NoSelectionException, SystematikQTreeWidgetItem
from PyQt5 import sip, QtCore
from PyQt5.QtCore import QSize
from asb_systematik.SystematikDao import AlexandriaDbModule, NODE_TYPE_VIRTUAL,\
    NODE_TYPE_NORMAL

class NewSubpointSelectionDialog(QDialog):
    
    def __init__(self, identifiers):
        super().__init__()

        self.identifiers = identifiers
        self.buttons = []
        
        
        self.setWindowTitle("Neuen Unterpunkt auswählen")

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        buttonBox = QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Bitte neuen Unterpunkt auswählen:"))
        self.buttons = []
        for identifier in identifiers:
            button = QRadioButton("%s" % identifier)
            self.buttons.append(button)
            layout.addWidget(button)
        
        layout.addWidget(buttonBox)
        
        self.setLayout(layout)
        
    def get_selected(self):
        
        for index in range(0,len(self.buttons)):
            if self.buttons[index].isChecked():
                return self.identifiers[index]
        
        return None
                
class DescriptionEditDialog(QDialog):
    
    def __init__(self, item):
        super().__init__()
        
        self.item = item
        
        self.setWindowTitle("Beschreibung Bearbeiten")
        self.resize(QSize(500, 100))
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        
        systematik = QLabel("Systematikpunkt: %s" % item.systematik_node.identifier)
        self.layout.addWidget(systematik)

        label = QLabel("Beschreibung:")
        self.layout.addWidget(label)
        beschreibung_entry = QLineEdit()
        beschreibung_entry.setText(item.systematik_node.beschreibung)
        beschreibung_entry.textChanged.connect(self.update_beschreibung)
        self.layout.addWidget(beschreibung_entry)

        self.virtual_checkbox = QCheckBox("Virtueller Systematikpunkt ohne Bestand")
        self.virtual_checkbox.setChecked(self.item.systematik_node.nodetype == NODE_TYPE_VIRTUAL)
        self.layout.addWidget(self.virtual_checkbox)
        self.virtual_checkbox.stateChanged.connect(self.virtual_state_changed)

        label = QLabel("Kommentar:")
        self.layout.addWidget(label)
        self.kommentar_entry = QPlainTextEdit(item.systematik_node.kommentar)
        self.kommentar_entry.textChanged.connect(self.update_kommentar)
        self.layout.addWidget(self.kommentar_entry)
        
        label = QLabel("Entfernt:")
        self.layout.addWidget(label)
        self.entfernt_entry = QPlainTextEdit(item.systematik_node.entfernt)
        self.entfernt_entry.textChanged.connect(self.update_entfernt)
        self.layout.addWidget(self.entfernt_entry)

        label = QLabel("Anfangsjahr:")
        self.layout.addWidget(label)
        self.startjahr_entry = QLineEdit(self._format_jahr(item.systematik_node.startjahr))
        self.startjahr_entry.textChanged.connect(self.update_startjahr)
        self.layout.addWidget(self.startjahr_entry)

        label = QLabel("Abschlussjahr:")
        self.layout.addWidget(label)
        self.endjahr_entry = QLineEdit(self._format_jahr(item.systematik_node.endjahr))
        self.endjahr_entry.textChanged.connect(self.update_endjahr)
        self.layout.addWidget(self.endjahr_entry)

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
        
    def virtual_state_changed(self, state):

        if state == QtCore.Qt.Checked:
            self.item.systematik_node.nodetype = NODE_TYPE_VIRTUAL
        else:
            self.item.systematik_node.nodetype = NODE_TYPE_NORMAL
        
    def _format_jahr(self, jahr):
        
        if jahr is None:
            return ""
        else:
            return "%d" % jahr    
        
    def update_beschreibung(self, text):
        
        self.item.beschreibung = text

    def update_kommentar(self):
        
        self.item.kommentar = self.kommentar_entry.toPlainText()

    def update_entfernt(self):
        
        self.item.entfernt = self.entfernt_entry.toPlainText()

    def _check_jahr(self, widget):
        """
        Returns integer or none depending on the text entry value.
        If it is not an integer, the text entry will be reset to an
        empty string.
        """

        try:
            return int(widget.text())
        except Exception as e:
            widget.setText("")
        return None

    def update_startjahr(self, text):

        jahr = self._check_jahr(self.startjahr_entry)
        self.item.startjahr = jahr

    def update_endjahr(self, text):

        jahr = self._check_jahr(self.endjahr_entry)
        self.item.endjahr = jahr
                

class Window(QWidget):
    
    PUNKT, BESCHREIBUNG = range(2)
    
    @inject
    def __init__(self, tree_widget_service: SystematikTreeWidgetService):
        super().__init__()
        self.tree_widget_service = tree_widget_service
        self.tree_widget = tree_widget_service.create_tree_widget()
        self.create_widgets()
        self.setGeometry(400, 400, 1300, 600)
        self.setWindowTitle("ASB Systematik")

    def create_widgets(self):
        
        filter_box = QHBoxLayout()
        filter_box.addWidget(QLabel("Dynamische Suche:"))
        filter_input = QLineEdit()
        filter_box.addWidget(filter_input)
        filter_input.textChanged.connect(self.filter_changed)
        
        treeGroupBox = QGroupBox("ASB Systematik")
        treeLayout = QHBoxLayout()
        treeLayout.addWidget(self.tree_widget)
        treeGroupBox.setLayout(treeLayout)

        buttonGroup = QHBoxLayout()
        expandButton = QPushButton('Alles ausklappen')
        expandButton.setToolTip('Kompletten Baum ausklappen')
        expandButton.clicked.connect(self.expand_tree)
        collapseButton = QPushButton('Alles einklappen')
        collapseButton.setToolTip('Kompletten Baum einklappen')
        collapseButton.clicked.connect(self.collapse_tree)
        editButton = QPushButton('Bearbeiten')
        editButton.setToolTip('Beschreibung des ausgewählten Eintrags ändern')
        editButton.clicked.connect(self.edit_description)
        newSubButton = QPushButton('Unterpunkt anlegen')
        newSubButton.setToolTip('Legt einen neuen Systematikpunkt unterhalb\ndes ausgewählten Eintrags an')
        newSubButton.clicked.connect(self.new_sub_point)
        deleteButton = QPushButton("Löschen")
        deleteButton.clicked.connect(self.delete_point)
        deleteButton.setToolTip('Löscht den ausgewählten Systematikpunkt')
        buttonGroup.addWidget(expandButton)
        buttonGroup.addWidget(collapseButton)
        buttonGroup.addWidget(editButton)
        buttonGroup.addWidget(newSubButton)
        buttonGroup.addWidget(deleteButton)

        
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(filter_box)
        mainLayout.addWidget(treeGroupBox)
        mainLayout.addLayout(buttonGroup)
        self.setLayout(mainLayout)
        
        self.show()
    
    def edit_description(self):

        try:
            item_widget = self.tree_widget.first_selected()
            
            old_description = item_widget.beschreibung
            old_comment = item_widget.kommentar
            old_entfernt = item_widget.entfernt
            old_startjahr = item_widget.startjahr
            old_endjahr = item_widget.endjahr
            old_nodetype = item_widget.nodetype
            
            dlg = DescriptionEditDialog(item_widget)
            if dlg.exec():
                # Save if there are changes
                if item_widget.beschreibung != old_description or \
                   item_widget.kommentar != old_comment or \
                   item_widget.entfernt != old_entfernt or \
                   item_widget.startjahr != old_startjahr or \
                   item_widget.nodetype != old_nodetype or \
                   item_widget.endjahr != old_endjahr:
                    self.tree_widget_service.save(item_widget)
            else:
                # Reset after cancel
                item_widget.beschreibung = old_description
                item_widget.kommentar = old_comment
                item_widget.entfernt = old_entfernt
                item_widget.startjahr = old_startjahr
                item_widget.endjahr = old_endjahr
                item_widget.nodetype = old_nodetype
                
        except NoSelectionException as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Keine Auswahl getroffen")
            msg.setText("Du mußt einen Eintrag auswählen!")
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Fehler!")
            msg.setText("Fehler:\n%s" % e)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
            
    def new_sub_point(self):

        try:
            parent_widget = self.tree_widget.first_selected()
            possible_children = parent_widget.systematik_node.get_possible_children()
            if len(possible_children) == 0:
                msg = QMessageBox(self)
                msg.setWindowTitle("Kein Kind-Punkt möglich")
                msg.setText("Für diesen Punkt kann kein Unterpunkt angelegt werden!")
                msg.setIcon(QMessageBox.Information)
                msg.exec()
                return
            if len(possible_children) > 1:
                dlg = NewSubpointSelectionDialog(possible_children)
                if dlg.exec():
                    selected = dlg.get_selected()
                    if selected is None:
                        return
                    child_widget = SystematikQTreeWidgetItem(parent_widget, selected)
                else:
                    return
            else:
                child_widget = SystematikQTreeWidgetItem(parent_widget, possible_children[0])
            parent_widget.setExpanded(True)
            dlg = DescriptionEditDialog(child_widget)
            if dlg.exec():
                self.tree_widget_service.save(child_widget)
            else:
                sip.delete(child_widget)
            
        except NoSelectionException as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Keine Auswahl getroffen")
            msg.setText("Du mußt einen Eintrag auswählen!")
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Fehler!")
            msg.setText("Fehler:\n%s" % e)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
    
    def delete_point(self):

        try:
            selected_widget = self.tree_widget.first_selected()
            node = selected_widget.systematik_node
            if len(node.children) > 0:
                msg = QMessageBox(self)
                msg.setWindowTitle("Fehler!")
                msg.setText("Eintrag hat noch Untereinträge!\nBitte erst die Untereinträge löschen!")
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                return
            if node.next_sibling is not None:
                msg = QMessageBox(self)
                msg.setWindowTitle("Fehler!")
                msg.setText("Es sind noch Einträge nach diesem Eintrag vorhanden!\nBitte erst die nachfolgenden Einträge löschen!")
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                return
            if node.next_sibling is not None:
                msg = QMessageBox(self)
                msg.setWindowTitle("Fehler!")
                msg.setText("Es sind noch Eintrag nach diesem Eintrag vorhanden!\nBitte erst die nachfolgenden Einträge löschen!")
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                return
            if self.tree_widget_service.is_used(selected_widget):
                msg = QMessageBox(self)
                msg.setWindowTitle("Fehler!")
                usage = self.tree_widget_service.first_usage(selected_widget)
                msg.setText("Der Eintrag wird benutzt und kann nicht\ngelöscht werden!\n(%s)" % usage)
                msg.setIcon(QMessageBox.Critical)
                msg.exec()
                return
            
            dlg = QMessageBox(self)
            dlg.setWindowTitle("Bestätigung")
            dlg.setText('Willst du wirklich den Systematikpunkt\n"%s"\nlöschen?' % node)
            dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            dlg.setIcon(QMessageBox.Question)
            button = dlg.exec()

            if button == QMessageBox.Yes:
                self.tree_widget_service.delete(selected_widget)
                sip.delete(selected_widget)
            else:
                pass

        except NoSelectionException as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Keine Auswahl getroffen")
            msg.setText("Du mußt einen Eintrag auswählen!")
            msg.setIcon(QMessageBox.Warning)
            msg.exec()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle("Fehler!")
            msg.setText("Fehler:\n%s" % e)
            msg.setIcon(QMessageBox.Critical)
            msg.exec()
        
    def expand_tree(self):
        
        self.tree_widget.expand_all()
    
    def collapse_tree(self):
        
        self.tree_widget.collapse_all()
        
    def filter_changed(self, filter_text):
        
        self.tree_widget.filter(filter_text.upper())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    injector = Injector([AlexandriaDbModule])
    window = injector.get(Window)
    window.show()
    sys.exit(app.exec_())
