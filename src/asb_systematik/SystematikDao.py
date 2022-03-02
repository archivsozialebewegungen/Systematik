'''
Created on 30.06.2021

@author: michael
'''
import re
from injector import singleton, inject, Module, provider, Injector
from sqlalchemy.engine.base import Connection, Engine
from sqlalchemy.sql.schema import Table, MetaData, Column, UniqueConstraint
from sqlalchemy.sql.sqltypes import String, Integer
from sqlalchemy.sql.expression import select, insert, update, and_, text, delete
from sqlalchemy.engine.create import create_engine
import os

roemisch = ('', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII',
            'XVIII', 'XIX', 'XX', 'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII', 'XXIX', 'XXX')

NODE_TYPE_NORMAL = 0
NODE_TYPE_VIRTUAL = 1

ALEXANDRIA_METADATA = MetaData()

SYSTEMATIK_TABLE = Table(
    'systematik',
    ALEXANDRIA_METADATA,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('punkt', String, nullable=False),
    Column('roemisch', Integer),
    Column('sub', Integer),
    Column('beschreibung', String, nullable=False),
    Column('kommentar', String, nullable=True),
    Column('entfernt', String, nullable=True),
    Column('startjahr', Integer, nullable=True),
    Column('endjahr', Integer, nullable=True),
    Column('nodetype', Integer, nullable=True),
    Column('digistate', Integer, nullable=True)
)

class NoDataException(Exception):
    pass


class DataError(Exception):
    
    def __init__(self, message):
        self.message = message

class DeletionForbiddenException(Exception):

    pass

class SystematikIdentifier:

    def __init__(self, punkt, roemisch=None, sub=None):
        """
        Initialization is possible in two ways: Either with
        punkt, roemisch and sub like in the database.
        Or with a full string including the roemisch and sub
        part, then this string will be split.
        """
        
        self.roemisch = roemisch
        if self.roemisch == 0:
            self.roemisch = None
        self.sub = sub
        if self.sub == 0:
            self.sub = None
        if punkt is None:
            self.punkt = None
            return
        
        self.punkt = self._sanitize_punkt(punkt)
        
        matcher = re.match('.*[IVX-].*', self.punkt)
        if matcher is not None:
            self._reinit_from_full_string()
            
    def _sanitize_punkt(self, punkt):
        
        if punkt is None:
            return None
        # whitespace
        punkt = re.sub('\s+', '', punkt)
        # trailing dots
        punkt = re.sub('\.$', '', punkt)
        
        return punkt
        
    def _reinit_from_full_string(self):
        
        punkte = self.punkt.split('.')
        self.punkt = '.'.join(punkte[:-1])
        
        subsplit = punkte[-1].split('-')
        if len(subsplit) == 2:
            self.sub = int(subsplit[1])
        else:
            self.sub = None
        if subsplit[0] in roemisch:
            for i in range(0,len(roemisch)):
                if roemisch[i] == subsplit[0]:
                    self.roemisch = i
        else:
            self.punkt = "%s.%s" % (self.punkt, subsplit[0])        
        
    def is_root(self):
        
        return self.punkt is None
        
    def _get_parent_identifier(self):
        
        if self.sub is not None:
            # This is correct even if self.roemisch is None
            return SystematikIdentifier(punkt=self.punkt, roemisch=self.roemisch)
        if self.roemisch is not None:
            return SystematikIdentifier(punkt=self.punkt)
        if self.punkt is None:
            raise Exception("Root node has no parent")
        
        punkte = self.punkt.split('.')
        
        if len(punkte) == 1:
            return SystematikIdentifier(None)
        
        return '.'.join(punkte[:-1])
    
    def _get_next_sibling(self):
        
        if self.punkt is None:
            return None
        if self.sub is not None:
            return SystematikIdentifier(self.punkt, self.roemisch, self.sub + 1)
        if self.roemisch is not None:
            return SystematikIdentifier(self.punkt, self.roemisch + 1)
        points = self.punkt.split('.')
        points[-1] = "%d" % (int(points[-1]) + 1)
        return SystematikIdentifier('.'.join(points))
    
    def get_next_siblings(self, maximum=3):
        
        siblings = []
        if self.next_sibling is None:
            return siblings
        siblings.append(self.next_sibling)
        for i in range(0,maximum-1):
            following = siblings[-1]._get_next_sibling()
            if following is None:
                break
            siblings.append(following)
            
        return siblings
    
    def _get_child_options(self):
        
        if self.punkt is None:
            return [SystematikIdentifier("0"), SystematikIdentifier("1")]
        if self.sub is not None:
            return []
        if self.roemisch is not None:
            return [SystematikIdentifier(self.punkt, self.roemisch, 1)]
        return [SystematikIdentifier("%s.0" % self.punkt),
                SystematikIdentifier("%s.1" % self.punkt),
                SystematikIdentifier(self.punkt, roemisch=1),
                SystematikIdentifier(self.punkt, sub=1),
                ]
    
    def _db_roemisch(self):
        
        if self.roemisch is None:
            return 0
        return self.roemisch
    
    def _db_sub(self):
        
        if self.sub is None:
            return 0
        return self.sub

    def __str__(self):
        
        if self.sub is not None:
            if self.roemisch is None:
                return "%s-%d" % (self.punkt, self.sub)
            else:
                return "%s.%s-%d" % (self.punkt, roemisch[self.roemisch], self.sub)
        if self.roemisch is not None:
            return "%s.%s" % (self.punkt, roemisch[self.roemisch])
        if self.punkt is None:
            return "Rootnode"
        return self.punkt
    
    def __eq__(self, other):
        
        return other.punkt == self.punkt and other.roemisch == self.roemisch and other.sub == self.sub
    
    def __hash__(self):
        
        return hash("%s" % self)
        
    parent = property(_get_parent_identifier)
    next_sibling = property(_get_next_sibling)
    child_options = property(_get_child_options)
    db_roemisch = property(_db_roemisch)
    db_sub = property(_db_sub)
        
class SystematikNode:
    """
    This class represents 1:1 the database table Systematik, null values in the
    database are represented as None
    """
    
    def __init__(self, identifier: SystematikIdentifier, beschreibung: str,
                 kommentar=None, entfernt=None, startjahr=None, endjahr=None,
                 nodetype=None,
                 digistate=None,
                 id=None):
        
        self.identifier = identifier
        self.beschreibung = beschreibung
        self.kommentar = kommentar
        self.entfernt = entfernt
        self.startjahr = startjahr
        self.nodetype = nodetype
        self.digistate = digistate
        self.id = id
        self.endjahr = endjahr
        self.parent = None
        self.children = []
        self.previous_sibling = None
        self.next_sibling = None

    def __iter__(self):
        
        return self
    
    def __next__(self):
        
        if len(self.children) > 0:
            return self.children[0]
        if self.next_sibling is not None:
            return self.next_sibling
        
    def __str__(self):
        
        return "%s: %s" % (self.identifier, self.beschreibung)
    
    def is_sub(self):
        
        return self.identifier.sub is not None
    
    def is_roman(self):
        
        return self.identifier.roemisch is not None
    
    def is_visible(self, description_filter):
        
        if description_filter in self.beschreibung.upper():
            return True
        
        for child in self.children:
            if child.is_visible(description_filter):
                return True
            
        return False
    
    def get_depth(self):
        
        if self.identifier.punkt is None:
            return 0
        return len(self.identifier.punkt.split('.'))

    def get_possible_children(self):
        
        if self.is_sub():
            # You can't create a sub point at the end of a branch
            return []
        
        last_child = None
        if len(self.children) > 0:
            last_child = self.children[-1]
            
        if last_child is None:
            if self.is_roman():
                # Only a sub is possible as child of a roman identifier
                return [SystematikNode(SystematikIdentifier(self.identifier.punkt, self.identifier.roemisch, 1), "Keine Beschreibung")]
            # if it's a simple point, a deeper point or a roman is possible
            return [SystematikNode(SystematikIdentifier(self.identifier.punkt, 1), "Keine Beschreibung"),
                    SystematikNode(SystematikIdentifier(self.identifier.punkt + ".1"), "Keine Beschreibung")]

        if last_child.is_sub():
            return [SystematikNode(SystematikIdentifier(last_child.identifier.punkt, last_child.identifier.roemisch, last_child.identifier.sub + 1), "Keine Beschreibung")]
        if last_child.is_roman():
            # Take the next roman, if we already have roman children
            return [SystematikNode(SystematikIdentifier(last_child.identifier.punkt, last_child.identifier.roemisch + 1), "Keine Beschreibung")]

        # increase the last point entry
        points = last_child.identifier.punkt.split('.')
        points[-1] = "%s" % (int(points[-1]) + 1)
        punkt = '.'.join(points)
        return [SystematikNode(SystematikIdentifier(punkt), "Keine Beschreibung")]
    
    def get_main_point_identifier(self):

        points = self.identifier.punkt.split('.')
        if len(points) == None:
            return SystematikIdentifier(None)
        else:
            return SystematikIdentifier(points[0])
        
class SystematikTreeIterator:
    
    def __init__(self, root_node):
        self.stack = [root_node]

    def __iter__(self):
        return self

    def __next__(self):
        if not self.stack: raise StopIteration
        node = self.stack.pop(0)
        self.stack = node.children + self.stack
        return node

class SystematikTree:
    
    def __init__(self, node_hash):
        
        self.rootnode = SystematikNode(SystematikIdentifier(None), "Archiv Soziale Bewegungen")
        node_hash = self._append_next_node(self.rootnode, node_hash)
        try:
            assert(len(node_hash) == 0)
        except AssertionError:
            for node in node_hash.values():
                print(node)
                
    def find_node(self, identifier):
        
        for node in self.iterator:
            if node.identifier == identifier:
                return node
        return None
                
    def _append_next_node(self, current_node: SystematikNode, node_hash):
        
        # There are missing siblings in the chain, so we look a bit ahead
        for next_sibling_identifier in current_node.identifier.get_next_siblings():
            if next_sibling_identifier in node_hash:
                next_sibling = node_hash[next_sibling_identifier]
                del(node_hash[next_sibling_identifier])
                next_sibling.previous_sibling = current_node
                current_node.next_sibling = next_sibling
                next_sibling.parent = current_node.parent
                next_sibling.parent.children.append(next_sibling)
                node_hash = self._append_next_node(next_sibling, node_hash)
                break
        for child_identifier in current_node.identifier.child_options:
            if child_identifier in node_hash:
                child = node_hash[child_identifier]
                del(node_hash[child_identifier])
                current_node.children.append(child)
                child.parent = current_node
                node_hash = self._append_next_node(child, node_hash)
                break
        return node_hash
    
    def _get_iterator(self):
        
        return SystematikTreeIterator(self.rootnode)    
    
    def __str__(self):

        string = ""        
        for node in self.iterator:
            string += "%s: %s\n" % (node.identifier, node.beschreibung)
        return string
    
    iterator = property(_get_iterator)
        
    
@singleton        
class SystematikDao:

    @inject
    def __init__(self, connection: Connection):

        self.connection = connection
    
    def fetch_by_identifier_object(self, identifier: SystematikIdentifier):
        
        stmt = select([SYSTEMATIK_TABLE]).where(
            and_(SYSTEMATIK_TABLE.c.punkt == identifier.punkt,
                 SYSTEMATIK_TABLE.c.roemisch == identifier.db_roemisch,
                 SYSTEMATIK_TABLE.c.sub == identifier.db_sub))
        record = self.connection.execute(stmt).fetchone()
        
        try:
            syst = self._map_to_node(record)
        except TypeError:
            raise NoDataException
        return syst
    
    def fetch_by_id(self, id: Integer) -> SystematikNode:
        
        stmt = select([SYSTEMATIK_TABLE]).where(SYSTEMATIK_TABLE.c.id == id)
        record = self.connection.execute(stmt).fetchone()
        
        try:
            syst = self._map_to_node(record)
        except TypeError:
            raise NoDataException
        return syst

    def fetch_tree(self, tree_implementation):
        
        result = self.connection.execute(select([SYSTEMATIK_TABLE]))
        nodes = {}
        for row in result.fetchall():
            node = self._map_to_node(row)
            nodes[node.identifier] = node
        return tree_implementation(nodes)

    def _map_to_node(self, record):

        identifier = SystematikIdentifier(record[SYSTEMATIK_TABLE.c.punkt],
                                          record[SYSTEMATIK_TABLE.c.roemisch],
                                          record[SYSTEMATIK_TABLE.c.sub])
        return SystematikNode(identifier=identifier,
                            beschreibung=record[SYSTEMATIK_TABLE.c.beschreibung], 
                            kommentar=record[SYSTEMATIK_TABLE.c.kommentar],
                            entfernt=record[SYSTEMATIK_TABLE.c.entfernt],
                            startjahr=record[SYSTEMATIK_TABLE.c.startjahr],
                            endjahr=record[SYSTEMATIK_TABLE.c.endjahr],
                            nodetype=record[SYSTEMATIK_TABLE.c.nodetype],
                            digistate=record[SYSTEMATIK_TABLE.c.digistate],
                            id=record[SYSTEMATIK_TABLE.c.id]
                            )
    
    def insert_node(self, node):
        
        stmt = insert(SYSTEMATIK_TABLE).\
            values(punkt=node.identifier.punkt, roemisch=node.identifier.db_roemisch,
                   sub=node.identifier.db_sub, beschreibung=node.beschreibung,
                   kommentar=node.kommentar,
                   entfernt=node.entfernt,
                   startjahr=node.startjahr,
                   endjahr=node.endjahr,
                   nodetype=node.nodetype,
                   digistate=node.digistate
                   )
        self.connection.execute(stmt)
        
    def delete_node(self, node):
        
        if node.next_sibling is not None:
            raise DeletionForbiddenException()
        
        if len(node.children) > 0:
            raise DeletionForbiddenException()
        
        if self.is_used(node.identifier):
            raise DeletionForbiddenException()
        
        stmt = delete(SYSTEMATIK_TABLE).where(SYSTEMATIK_TABLE.c.punkt == node.identifier.punkt,
                                              SYSTEMATIK_TABLE.c.roemisch == node.identifier.db_roemisch,
                                              SYSTEMATIK_TABLE.c.sub == node.identifier.db_sub)
        self.connection.execute(stmt)
        
    def update_node(self, node):
        
        roemisch = node.identifier.roemisch
        if roemisch is None:
            roemisch = 0
        sub = node.identifier.sub
        if sub is None:
            sub = 0
        stmt = update(SYSTEMATIK_TABLE).\
            values(beschreibung=node.beschreibung,
                   kommentar=node.kommentar,
                   entfernt=node.entfernt,
                   startjahr=node.startjahr,
                   nodetype=node.nodetype,
                   endjahr=node.endjahr).\
            where(and_(SYSTEMATIK_TABLE.c.punkt == node.identifier.punkt,
                       SYSTEMATIK_TABLE.c.roemisch == roemisch,
                       SYSTEMATIK_TABLE.c.sub == sub))
        self.connection.execute(stmt)
    
    def exists(self, identifier):

        stmt = text("select 1 from systematik where punkt = '%s' and roemisch = %d and sub = %d" % 
                    (identifier.punkt, identifier.db_roemisch, identifier.db_sub))
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return True
        
        return False
    
    def is_used(self, identifier):
        """Systematik identifiers are used in a lot of places, without constraint. This
        checks all of these places, if the given identifier is used."""
        
        stmt = text("select 1 where exists (select 1 from broschueren where systematik1 = " + 
                    "'%s' or systematik2 = '%s')" % (identifier, identifier))
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return True
    
        stmt = text("select 1 where exists (select 1 from zeitschriften where systematik1 = '%s' " % identifier +
                    "or systematik2 = '%s' or systematik3 = '%s')" % (identifier, identifier))
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return True
        
        stmt = text("select 1 where exists (select 1 from dokument where standort = '%s')" % identifier)
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return True

        stmt = text("select 1 where exists (select 1 from sverweis where systematik = '%s' and roemisch = %d and sub = %d)" % 
                    (identifier.punkt, identifier.db_roemisch, identifier.db_sub))
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return True

        return False

    def get_first_usage(self, identifier):
        
        brosch_titel = self.get_first_brosch_usage(identifier)
        if brosch_titel != None:
            return "Broschüre \"%s\"" % brosch_titel
        zeitsch_titel = self.get_first_zeitsch_usage(identifier)
        if zeitsch_titel != None:
            return "Zeitschrift \"%s\"" % zeitsch_titel
        alex_id = self.get_first_alexandria_usage(identifier)
        if alex_id != None:
            return "Alexandria-Dokument Nr. %d" % alex_id
        
        raise Exception("Keine Nutzung für Systematikpunkt %s gefunden!" % identifier)

    def get_first_zeitsch_usage(self, identifier):

        stmt = text("select titel from zeitschriften where systematik1 = '%s' " % identifier +
                    "or systematik2 = '%s' or systematik3 = '%s' limit 1" % (identifier, identifier))
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return row['titel']
        return None

    def get_first_brosch_usage(self, identifier):

        stmt = text("select titel from broschueren where systematik1 = " + 
                    "'%s' or systematik2 = '%s' limit 1" % (identifier, identifier))
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return row['titel']
        return None
    
    def get_first_alexandria_usage(self, identifier):
        
        stmt = text("select hauptnr from dokument where standort = '%s' limit 1" % identifier)
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return row['hauptnr']
        
        stmt = text("select hauptnr from sverweis where systematik = '%s' and roemisch = %d and sub = %d limit 1" % 
                    (identifier.punkt, identifier.db_roemisch, identifier.db_sub))
        result = self.connection.execute(stmt)
        for row in result.fetchall():
            return row['hauptnr']
        
        return None
    
    def fetch_root_node(self, node: SystematikNode):
        
        root_node_identifier = node.get_main_point_identifier()
        return self.fetch_by_identifier_object(root_node_identifier)

@singleton    
class JoinChecker:
    
    @inject
    def __init__(self, connection: Connection):

        self.connection = connection
        
        self.columns = [
            {"id": "hauptnr", "table": "dokument", "column": "standort"},
            {"id": "id", "table": "zeitschriften", "column": "systematik1"},
            {"id": "id", "table": "zeitschriften", "column": "systematik2"},
            {"id": "id", "table": "zeitschriften", "column": "systematik3"},
            {"id": "id", "table": "broschueren", "column": "systematik1"},
            {"id": "id", "table": "broschueren", "column": "systematik2"}
        ]
        
    def run_check(self):
        
        for column in self.columns:
            stmt = text("select %s as id, %s as systematik from %s" % (column['id'], column['column'], column['table']))
            result = self.connection.execute(stmt)
            for row in result.fetchall():
                punkt = row['systematik']
                if punkt is None or punkt == '':
                    continue
                try:
                    identifier = SystematikIdentifier(punkt)
                except Exception:
                    print("Fehler in tabelle %s bei id %s: %s" % (column['table'], row['id'], row['systematik']))
        
class AlexandriaDbModule(Module):

    @singleton
    @provider
    def provide_engine(self) -> Engine:
        return create_engine(os.environ['DB_URL'])

    @singleton
    @provider
    @inject
    def provide_connection(self, engine: Engine) -> Connection:
        return engine.connect()

if __name__ == '__main__':

    injector = Injector([AlexandriaDbModule])

    join_checker = injector.get(JoinChecker)
    join_checker.run_check()
