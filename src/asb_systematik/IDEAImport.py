'''
Created on 16.08.2023

@author: michael
'''
import os
import csv
import re
from asb_systematik.SystematikDao import SystematikDao, AlexandriaDbModule,\
    SystematikIdentifier, NoDataException, SystematikNode
from injector import singleton, inject, Injector
import datetime

class Interview(object):
    
    def __init__(self, csv_row):
        
        self.signatur = SystematikIdentifier(csv_row[0])
        self.laufnr = csv_row[1]
        self.zeitzeugin = csv_row[2]
        self.interview_laenge = csv_row[3]
        self.interview_datum = self._create_date_fields(csv_row[4])
        self.sprachen = self._split_multivalue_field(csv_row[5])
        self.interviewerin = csv_row[6]
        self.transkript = self._evaluate_boolean_field(csv_row[7])
        self.kontextmaterial = self._evaluate_boolean_field(csv_row[8])
        self.podcast = self._evaluate_boolean_field(csv_row[9])
        self.sperrvermerk = self._evaluate_boolean_field(csv_row[10])
        self.geburtsjahr = csv_row[11]
        self.biographische_regionen = self._reformat_regions(csv_row[12])
        self.beruf = self._split_multivalue_field(csv_row[13])
        self.migrationsgrund = csv_row[14]
        self.schlagworte = self._split_multivalue_field(csv_row[15])
        self.vermerk = csv_row[16]
        
    def __str__(self):
        
        string = "%s\n" % self.zeitzeugin
        
        string += "  Signatur: %s\n" % self.signatur
        string += "  Laufnr: %s\n" % self.laufnr
        string += "  Länge des Interviews: %s\n" % self.interview_laenge
        string += self._show_multiline_field(self.interview_datum, "Aufnahmedatum")
        string += self._show_multiline_field(self.sprachen, "Sprachen")
        string += "  Interviewerin: %s\n" % self.interviewerin
        string += self._show_boolean_field(self.transkript, "Transkript")
        string += self._show_boolean_field(self.kontextmaterial, "Kontextmaterial")
        string += self._show_boolean_field(self.podcast, "Podcast")
        string += self._show_boolean_field(self.sperrvermerk, "Sperrvermerk")
        string += "  Geburtsjahr: %s\n" % self.geburtsjahr
        string += self._show_multiline_field(self.biographische_regionen, "Biographische Regionen")
        string += self._show_multiline_field(self.beruf, "Berufe")
        string += "  Migrationsgrund: %s\n" % self.migrationsgrund
        string += self._show_multiline_field(self.schlagworte, "Schlagworte")
        if self.vermerk:
            string += "  Vermerk: %s\n" % self.vermerk
                    
        return string
    
    def _reformat_regions(self, field):
        
        regions = []
        sub_fields = re.split(r'\s*[;]\s*', field.strip())
        for sub_field in sub_fields:
            try:
                country, cities = re.split("\s*:\s*", sub_field)
            except ValueError:
                regions.append(sub_field)
                continue
            city_list = self._split_multivalue_field(cities)
            for city in city_list:
                regions.append("%s (%s)" % (city, country))
        return regions
    
    def _create_date_fields(self, field):
        
        dates = []
        
        sub_fields = self._split_multivalue_field(field)
        for sub_field in sub_fields:
            try:
                dates.append(datetime.datetime.strptime(sub_field, "%d.%m.%y").date())
            except ValueError:
                try:
                    dates.append(datetime.datetime.strptime(sub_field, "%d.%m.%Y").date())
                except ValueError:
                    pass
        
        return dates
    
    def _split_multivalue_field(self, field):
        
        sub_fields = re.split(r'\s*[;,]\s*', field.strip())
        if sub_fields[-1] == "":
            return sub_fields[:-1]
        return sub_fields
    
    def _evaluate_boolean_field(self, field):
        
        return "ja" in field.lower()
    
    def _show_boolean_field(self, field, desc):

        if field:
            return "  %s vorhanden\n" % desc
        else:
            return "  Kein %s vorhanden\n" % desc

    def _show_multiline_field(self, field, title):
        
        string = "  %s:\n" % title
        for value in field:
            string += "    %s\n" % value
        return string

@singleton
class CSVReader(object):
    
    @inject
    def __init__(self):
        
        self.csv_file_name = os.path.join(os.path.dirname(__file__), "data", "idea.csv")
        
    def get_interviews(self):
        
        interviews = []
        with open(self.csv_file_name, newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                if row[0] == "Bestell-Signatur":
                    continue
                interviews.append(Interview(row))
                
        return interviews

@singleton
class SystematikWriter(object):
    
    @inject
    def __init__(self, csv_reader: CSVReader, systematik_dao: SystematikDao):
        
        self.csv_reader = csv_reader
        self.systematik_dao = systematik_dao
    
    def write_interviews(self):

        interviews = self.csv_reader.get_interviews()
        for interview in interviews:
            try:
                systematik_node = self.systematik_dao.fetch_by_identifier_object(interview.signatur)
            except NoDataException:
                print("Lege Systematikpunkt %s an!" % interview.signatur)
                systematik_node = self._create_systematik_node(interview)
            
            if interview.sperrvermerk:
                systematik_node = SystematikNode(systematik_node.identifier,
                                                 "%0.2d IDEA Noch nicht freigegeben" % interview.signatur.roemisch)
                self.systematik_dao.update_node(systematik_node)
                continue
            
            systematik_node.kommentar = "%s." % interview.interview_laenge
            if len(interview.sprachen) == 1:
                systematik_node.kommentar += " Sprache: %s." % interview.sprachen[0]
            else:
                systematik_node.kommentar += " Sprachen: %s." % ", ".join(interview.sprachen)
            if interview.podcast:
                systematik_node.kommentar += " Podcast vorhanden."
            if interview.kontextmaterial:
                systematik_node.kommentar += " Kontextmaterial vorhanden."
            systematik_node.kommentar += "\nIW: %s. ZZ ist Jg. %s." % (interview.interviewerin, interview.geburtsjahr)
            if len(interview.biographische_regionen) == 1:
                systematik_node.kommentar += "\nBiographische Region: %s." % interview.biographische_regionen[0]
            else:
                systematik_node.kommentar += "\nBiographische Regionen: %s." % ", ".join(interview.biographische_regionen)
            systematik_node.kommentar += "\nMigrationsanlass: %s." % (interview.migrationsgrund)
            if len(interview.beruf) == 1:
                systematik_node.kommentar += "\nBeruf: %s." % interview.beruf[0]
            else:
                systematik_node.kommentar += "\nBerufe: %s." % ", ".join(interview.beruf)
            if len(interview.schlagworte) == 1:
                systematik_node.kommentar += "\nStichwort: %s." % interview.schlagworte[0]
            else:
                systematik_node.kommentar += "\nStichworte: %s." % ", ".join(interview.schlagworte)
            
            systematik_node.startjahr = self._get_min_year(interview.interview_datum)
            systematik_node.endjahr = self._get_max_year(interview.interview_datum)
                
            systematik_node.beschreibung = "%0.2d IDEA %s" % (interview.signatur.roemisch, interview.zeitzeugin)
            
            self.systematik_dao.update_node(systematik_node)
    
    def _get_min_year(self, dates):
        
        if len(dates) == 0:
            return None

        min_year = dates[0].year
        for date in dates[1:]:
            if min_year > date.year:
                min_year = date.year
        return min_year
    
    def _get_max_year(self, dates):
        
        if len(dates) == 0:
            return None
        
        max_year = dates[0].year
        for date in dates[1:]:
            if max_year < date.year:
                max_year = date.year
        return max_year

    def _create_systematik_node(self, interview):
        
        node = SystematikNode(interview.signatur, "Unkonfiguriertes IDEA Interview")
        self.systematik_dao.insert_node(node)
        return node
        
if __name__ == '__main__':
    
    injector = Injector([AlexandriaDbModule])
    writer = injector.get(SystematikWriter)
    writer.write_interviews()
    
    reader = CSVReader()
