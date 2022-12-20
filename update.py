#!/usr/bin/env python
import csv
import sys
import configparser
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import html2text
import argparse
from pathlib import Path

class Captain:
    ''' A Captain knows the name of his team along with his own name and email.'''
    def __init__(self, team, given, surname, email):
        self.team = team
        self.given = given
        self.surname = surname
        self.email = email

    def __str__(self):
        return self.team + ": " + self.given + " " + self.surname + " <" + self.email +">"

class League:
    ''' A specific league with its name and set of captains. '''
    def __init__(self,name,captainGames,people):
        ''' Store the set of matches to be played. '''
        self.name = name
        self.captainGames = captainGames
        self.matches = {}
        self.games = []
        self.planned_game_count = {}
        self.min_game_count = {}
        self.people = people
        for cg1 in captainGames:
            c1, g1 = cg1
            for cg2 in captainGames:
                c2, g2 = cg2
                if c1.team < c2.team:
                    self.matches[c1.team, c2.team] = []
                    self.planned_game_count[c1.team, c2.team] =  min(g1,g2)
                    self.min_game_count[c1.team, c2.team] = (self.planned_game_count[c1.team, c2.team] + 2)//2

    def __str__(self):
        p = "League:" + self.name
        completed = 0
        started = 0
        for m in self.matches:
            mc = len(self.matches[m])
            if mc >= self.min_game_count[m]: completed += 1
            elif mc > 0: started += 1

        return p + ", Completed:" + str(completed) + ", Started:" + str(started) + ", Not started:" + str(len(self.matches) - completed - started) 
    
    def record(self, h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue, reporter, witness, timestamp):
        keyText =  "Game between " + h_name + " of " + h_team + " and " + a_name + " of " + a_team + " in " + self.name + " league at " + venue + " on " + date
        ''' Record a single result trapping some errors'''
        if h_score == a_score:
            print (keyText, "was recorded as drawn which is not an acceptable result.")
        elif (h_team < a_team): 
            key=h_team, a_team
            if key in self.matches:
                self.matches[key].append((h_score,a_score))
                self.games.append((h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue, reporter, witness, timestamp))
            else:
                print (keyText, "was unexpected.")
        else: 
            key=a_team, h_team
            if key in self.matches:
                self.matches[key].append((a_score, h_score))
                self.games.append((h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue, reporter, witness, timestamp))
            else:
                print (keyText, "was unexpected.")
                
    def gamesTable(self):
        ''' Produce a table (in json format) showing all the games played in the league. '''
        tdata = {}
        tdata['data'] = []
        rows = tdata['data']
        rows.append(("Home team","Home name", "Home hcap", "Home score", "Away team","Away name", "Away hcap", "Away score", "Peeling", "Date", "Venue"))
        for g in self.games:
            row = g
            rows.append(row)
        return json.dumps(tdata)

    def reportResults(self):
        '''email results to CroquetScores'''
        # Find those results already reported. The results are in a file
        # with multiple lines of json as you can't store the matches
        # structure directly
        alreadyDone = set()
        fname = "reports/"+self.name+".json"
        if Path(fname).is_file():
            with open(fname) as f:
                for jsonobj in f:
                    key, val = json.loads(jsonobj)
                    alreadyDone.add(tuple(key))
        matches = {}
        for g in self.games:
            key = (g[9], g[10], g[0], g[4])
            if key not in matches: matches[key]=[]
            if g[3] > g[7]:
                result = g[1] + " beat " + g[5] + " +" + str(g[3]-g[7]) + (g[8].lower() if g[3] == 26 else "(t)")
            else:
                result = g[5] + " beat " + g[1] + " +" + str(g[7]-g[3]) + (g[8].lower() if g[7] == 26 else "(t)")
            matches[key].append(result)
       
        for key, results in {key:val for key,val in matches.items() if key not in alreadyDone} .items():
            subject = "SCF " + self.name + " League " + key[2] + " vs " + key[3] + " at " + key[1] + " on " + key[0]
            html = "<p>"
            for result in results:
                html += result + "<br/>"
            html += "</p>"
            html += "<p>Steve Fisher <em>(SCF AC Leagues Manager)</em></p>"

            if sendHtmlMail(self.people["rankings"], subject, html, reportWanted):
                if reportWanted:
                    with open(fname,'w') as f:
                        for key, value in matches.items():
                            f.write(json.dumps([key,value]))
                            f.write("\n")

    def reportToOppos(self):
        '''email results to opposition and observer'''
        # Find those results already reported. The results are in a file
        # with multiple lines of json as you can't store the matches
        # structure directly

        # Read in set of keys already processed
        alreadyDone = set()
        fname = "reports/"+self.name+" oando.json"
        if Path(fname).is_file():
            with open(fname) as f:
                for jsonobj in f:
                    key = json.loads(jsonobj)
                    alreadyDone.add(tuple(key))
                    
        matches = {}
        meta = {}
        for g in self.games:
            key = (g[9], g[10], g[0], g[4])
            if key not in alreadyDone:
                if key not in matches:
                    matches[key]=[]
                    meta[key]=g[11:]
                result = list(g[1:4])
                result.extend(g[5:9])
                matches[key].append(tuple(result))
            
        for key, results in matches.items():
            report,witness,ts = meta[key]

            resultHtml = "<table><tr><th>Home</th><th>Name</th><th>Handicap</th><th>Hoops</th>"
            resultHtml += "<th>Away</th><th>Name</th><th>Handicap</th><th>Hoops</th><th>Code<th></tr>"
            for result in results:
                resultHtml += "<tr><td>" + key[2] + "</td><td>" + result[0] + "</td><td>" + result[1] + "</td><td>" + str(result[2]) + "</td>"
                resultHtml += "<td>" + key[3] + "</td><td>" + result[3] + "</td><td>" + result[4] + "</td><td>" + str(result[5]) + "</td><td>" + result[6] + "</td></tr>"
            resultHtml += "</table>"

            subject = "SCF " + self.name + " League " + key[2] + " vs " + key[3] + " at " + key[1] + " on " + key[0]

            html = "<p>" + witness + ",</p>"
            ts1, ts2 = ts.split(" ")
            html += "<p>The results below were reported by " + report + " on " + ts1 + " at " + ts2 +  "</p><p>"
            html += resultHtml + "</p>"
            html += "<p>Please report any disagreements.</p>"
            html += "<p>Steve Fisher <em>(SCF AC Leagues Manager)</em></p>"
 
            if sendHtmlMail([report,witness], subject, html, mailWanted):
                html = "<p>" + self.people["observer"] + ",</p>"
                html += "<p>The results below were reported by " + report + " on " + ts1 + " at " + ts2
                html += " and have just been sent to " + witness + " in case they wish to complain. </p><p>"
                html += resultHtml + "</p>"
                html += "<p>Steve Fisher <em>(SCF AC Leagues Manager)</em></p>"
                if sendHtmlMail(self.people["observer"], subject, html, mailWanted):
                    if mailWanted:
                        with open(fname,'a') as f:
                            f.write(json.dumps(key))
                            f.write("\n")
               
    def table(self):
        ''' Produce a league table (in json format). '''
        tdata = {}
        tdata['data'] = []
        rows = tdata['data']
        
        row = []
        rows.append(row)
        row.append("Team")
        for c1,g1 in self.captainGames:
            row.append(c1.team)
        row.extend(["Played","Pts","games"])
        
        for c1,g1 in self.captainGames:
            played = 0
            pts = 0
            games = 0
            row = []
            rows.append(row)
            row.append(c1.team)
            for c2,g2 in self.captainGames:
                c1score = 0
                c2score = 0
                if c1.team < c2.team:
                    matches = self.matches[c1.team, c2.team]
                    for res in matches:
                        if res[0] > res[1]:
                            c1score += 1
                            games += 1/self.planned_game_count[c1.team, c2.team]
                        else:
                            c2score += 1
                            games -= 1/self.planned_game_count[c1.team, c2.team]
                    row.append(str(c1score) +"-"+ str(c2score))
                    if len(matches) >= self.min_game_count[c1.team, c2.team]:
                        played += 1
                        if c1score > c2score: pts +=2
                        elif c1score == c2score: pts +=1
                elif c1.team > c2.team:
                    matches = self.matches[c2.team, c1.team]
                    for res in matches:
                        if res[0] > res[1]:
                            c2score += 1
                            games -= 1/self.planned_game_count[c2.team, c1.team]
                        else:
                            c1score += 1
                            games += 1/self.planned_game_count[c2.team, c1.team]
                    row.append(str(c1score) +"-"+ str(c2score))
                    if len(matches) >= self.min_game_count[c2.team, c1.team]:
                        played += 1
                        if c1score > c2score: pts +=2
                        elif c1score == c2score: pts +=1
                else: row.append("")
            row.append(str(played)) 
            row.append(str(pts))
            row.append(str(round(games,2)))
        
        return json.dumps(tdata)

def readConfig(configFile):
    ''' A config file has one section "files" to identify: corrections,
    results and captains. This reads it in.
    '''
   
    config=configparser.ConfigParser()
    config.read(configFile + ".ini")
    corrections = config.get("files","corrections")
    results = config.get("files", "results")
    captains = config.get("files", "captains")
    people = {}
    people["rankings"] = config.get("people","rankings")
    people["observer"] = config.get("people", "observer")               
    
    return captains, results, corrections, people

def getCordict(corrections):
    ''' Read the corrections file and return a dictionary indexed by
    timestamp. In the event of problems they are reported but the
    program continues. '''
    
    cordict = {}
    with open(corrections) as clist:
        for jsonobj in clist:
            if len(jsonobj.strip()) != 0:
                try:
                    cor = json.loads("{" + jsonobj + "}")
                except:
                    print ("Failed to process", jsonobj)
                ts = datetime.strptime(cor["ts"],"%d/%m/%Y %H:%M:%S")
                if ts in cordict:
                    print ("Corrections file has multiple occurences of timestamp", ts)
                else:
                    for key in cor.keys():
                    	if key not in ["ts","op","Email address", "Email of opponents captain","League","Date","Venue","Home team","Away team","Home player name 1","Home player handicap 1","Home player hoops scored 1","Away player name 1","Away player handicap 1","Away player hoops scored 1","Peeling abbreviation 1","Home player name 2","Home player handicap 2","Home player hoops scored 2","Away player name 2","Away player handicap 2","Away player hoops scored 2","Peeling abbreviation 2","Home player name 3","Home player handicap 3","Home player hoops scored 3","Away player name 3","Away player handicap 3","Away player hoops scored 3","Peeling abbreviation 3","Home player name 4","Home player handicap 4","Home player hoops scored 4","Away player name 4","Away player handicap 4","Away player hoops scored 4","Peeling abbreviation 4"]:
                    	    print("Unexpected field", key, "in", jsonobj)
                    cordict[ts] = {key:val for key,val in cor.items() if key != 'ts'}
    return cordict

def readResults(results, cordict):
    ''' Read and correct the results. Each result record has a key of
    league, date, venue, home_team and away_team. If a game has been
    recorded more than once an error message is displayed and results
    for that key will be removed.

    Returns: data - the good data as a list of rows 

    '''
    with open(results, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        data = {}
        keycount = {}
  
        for row in reader:
            ts = datetime.strptime(row['Timestamp'],"%d/%m/%Y %H:%M:%S")
            
            if ts in cordict:
                op = cordict[ts]['op']
                if op == "update":
                    updates = {key:val for key,val in cordict[datetime.strptime(row['Timestamp'],"%d/%m/%Y %H:%M:%S")].items() if key != 'op'}
                    for key, val in updates.items():
                        row[key]=val
                    del cordict[ts]
                elif op == "delete":
                    del cordict[ts]
                    continue
                else:
                    print ("Unexpected correction op", op)
                    del cordict[ts]
                
            home_team = row['Home team']
            away_team = row['Away team']
            league = row['League']
            date = row['Date']
            venue = row['Venue']
            key = (league, date, venue, home_team, away_team)
            if key not in data:
                data[key] = row
                keycount[key] = 1
            else:
                if keycount[key] == 1:
                    keycount[key] = 2
                    print ("Duplicate results for ",key, "submitted by", row['Email address'], "and", data[key]['Email address'])
                else:
                    keycount[key] += 1
                    
    # Only keep data reported once
    for multi in {key: val for key, val in keycount.items() if val > 1 }.keys():
        del data[multi]
  
    # Report other problems
    if cordict: print("Some corrections have not been applied", cordict)              

    return data.values()

def getLeagues(captains, people):
    ''' Derive an array of leagues indexed by name from the captains csv
    file.

    Returns: leagues - an array of Leagues indexed by name

    '''   
    A = set()
    B = set()
    C = set()
    HN = set()
    HS = set()
    leagues = {}
    names = ['A Level','B Level','C Level','Hcap N','Hcap S']
    ls = [A,B,C,HN,HS]
    with open(captains, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            captain = Captain(row['Club'], row['Given'], row['Surname'], row['Email'])
            for name,league in zip(names,ls):
            	if int(row[name]) > 1: league.add((captain,int(row[name])))

    for name,league in zip(names,ls):
        leagues[name] = League(name, league, people)
    return leagues

def populateLeagues(data, leagues):
    '''Populate the leagues.'''
    for datum in data:
        date = datum["Date"]
        venue = datum["Venue"]
        league_name = datum["League"]
        league = leagues[league_name]
        h_team = datum["Home team"]
        a_team = datum["Away team"]
        reporter = datum["Email address"]
        witness = datum["Email of opponents captain"]
        ts = datum["Timestamp"]
        for i in range(1,5):
            if len(datum['Home player hoops scored ' + str(i)].strip()) == 0: break
            h_score = int(datum['Home player hoops scored ' + str(i)])
            a_score = int(datum['Away player hoops scored ' + str(i)])
            h_name = datum['Home player name ' + str(i)]
            a_name = datum['Away player name ' + str(i)]
            h_handicap = datum['Home player handicap ' + str(i)]
            a_handicap = datum['Away player handicap ' + str(i)]
            pa = datum['Peeling abbreviation ' + str(i)]
            league.record(h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue, reporter, witness, ts)

def sendHtmlMail(to, subject, html, actionWanted):
    '''Send an email

    Parameters: to - email of intended recipient
                subject - subject field
                text - main body of the message to send as plain text
                html - main body of the message as HTML
                '''

    username = "ac-leagues-manager@southern-croquet.org.uk"
    with open("password") as p:
        password = p.readline().rstrip("\n")
    sender_email = username
    text_maker = html2text.HTML2Text()
    text_maker.ignore_emphasis = True
    text = text_maker.handle(html)

    if printWanted:
        print("\nTo: " + str(to) + "\nSubject: " + subject)
        for line in text.split("\n"):
            if line.strip() != "": print(line)

    if actionWanted:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = ",".join(to) if isinstance(to,list) else to
        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))
                           
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("mail.southern-croquet.org.uk", 465, context=context) as server:
            server.login(username, password)
#           server.set_debuglevel(1)
            try:
                fails = server.sendmail(sender_email,to,message.as_string())
            except smtplib.SMTPRecipientsRefused as inst:
                print (inst)
                return False
            if len(fails) >0: print (fails)
            return len(fails) == 0
    else:
        return True
        
def main():
    ''' Main program. '''

    parser = argparse.ArgumentParser(description="Process SCF league results.")
    parser.add_argument("-m", "--mailWanted", action="store_true", help="send emails")
    parser.add_argument("-r", "--reportWanted", action="store_true", help="send rankings")
    parser.add_argument("-v", "--verbose", action="store_true", help="list text version of emails that will be sent unless -n selected")
    parser.add_argument("-c", "--configfile", default="default")
    args = parser.parse_args()
    global mailWanted, printWanted, reportWanted
    mailWanted = args.mailWanted
    printWanted = args.verbose
    reportWanted = args.reportWanted

    # Find the config file and read it
    captains, results, corrections, people = readConfig(args.configfile)
   
    # Read in the file of corrections
    cordict = getCordict(corrections)
    
    # Now read the results
    data = readResults(results, cordict)

    # Find what matches should be played
    leagues = getLeagues(captains, people)
    
    # Now fill the league tales with results
    populateLeagues(data, leagues)
              
    # Now produce tables
    for name in leagues:
        league = leagues[name]
        print (league)
        with open("tables/"+name+"_table.json",'w') as f:
            f.write(league.table())
        with open("tables/"+name+"_games.json",'w') as f:
            f.write(league.gamesTable())
        if name in ("A Level", "B Level", "C Level"):
            league.reportResults()
            league.reportToOppos()
        
if __name__ == '__main__': main()
