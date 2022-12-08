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
    ''' A specific league with its name, set of captains and number of games in a match. '''
    def __init__(self,name,captains, game_count):
        ''' Store the minimum number of games for an outcome and the set of matches to be played. '''
        self.name = name
        self.captains = captains
        self.matches = {}
        self.games = []
        for c1 in captains:
            for c2 in captains:
                if c1.team < c2.team:
                    self.matches[c1.team, c2.team] = []
        self.min_game_count = (game_count +2)//2

    def __str__(self):
        p = "League:" + self.name
        completed = 0
        started = 0
        for m in self.matches:
            mc = len(self.matches[m])
            if mc >= self.min_game_count: completed += 1
            elif mc > 0: started += 1

        return p + ", Completed:" + str(completed) + ", Started:" + str(started) + ", Not started:" + str(len(self.matches) - completed - started) 
    
    def record(self, h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue, to):
        html =  "<p>Game between " + h_name + " of " + h_team + " and " + a_name + " of " + a_team + " in " + self.name + " league at " + venue + " on " + date + ".<p>"
        ''' Record a single result trapping some errors'''
        if h_score == a_score:
            html += "<p>This game was recorded as drawn which is not an acceptable result.</p>"
            html += htmlSign()
            sendMail(to,"Attempt to record drawn game", html)
        elif (h_team < a_team): 
            key=h_team, a_team
            if key in self.matches:
                self.matches[key].append((h_score,a_score))
                self.games.append((h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue))
            else:
                html += "<p>No games are expected</p>"
                html += htmlSign()
                sendMail(to,"Attempt to record unexpected game", html)
        else: 
            key=a_team, h_team
            if key in self.matches:
                self.matches[key].append((a_score, h_score))
                self.games.append((h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue))
            else:
                html += "<p>No games are expected</p>"
                html += htmlSign()
                sendMail(to,"Attempt to record unexpected game", html, True)
                
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

            sendMail("results@croquet.org.uk", subject, html, report=True)
            
            if reportWanted:
                with open(fname,'w') as f:
                    for key, value in matches.items():
                        f.write(json.dumps([key,value]))
                        f.write("\n")
               
    def table(self):
        ''' Produce a league table (in json format). '''
        tdata = {}
        tdata['data'] = []
        rows = tdata['data']
        
        row = []
        rows.append(row)
        row.append("Team")
        for c1 in self.captains:
            row.append(c1.team)
        row.extend(["Played","Pts"])
        
        for c1 in self.captains:
           
            played = 0
            pts = 0
            row = []
            rows.append(row)
            row.append(c1.team)
            for c2 in self.captains:
                c1score = 0
                c2score = 0
                if c1.team < c2.team:
                    matches = self.matches[c1.team, c2.team]
                    for res in matches:
                        if res[0] > res[1]: c1score += 1
                        else: c2score += 1
                    row.append(str(c1score) +"-"+ str(c2score))
                    if len(matches) >= self.min_game_count:
                        played += 1
                        if c1score > c2score: pts +=2
                        elif c1score == c2score: pts +=1
                elif c1.team > c2.team:
                    matches = self.matches[c2.team, c1.team]
                    for res in matches:
                        if res[0] > res[1]: c2score += 1
                        else: c1score += 1
                    row.append(str(c1score) +"-"+ str(c2score))
                    if len(matches) >= self.min_game_count:
                        played += 1
                        if c1score > c2score: pts +=2
                        elif c1score == c2score: pts +=1
                else: row.append("")
            row.append(str(played)) 
            row.append(str(pts))
        
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
    return captains, results, corrections

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
                    	if key not in ["ts","op","Email address", "Email of opponents captain","League","Date","Venue","Home team","Away Team","Home player name 1","Home player handicap 1","Home player hoops scored 1","Away player name 1","Away player handicap 1","Away player hoops scored 1","Peeling abbreviation 1","Home player name 2","Home player handicap 2","Home player hoops scored 2","Away player name 2","Away player handicap 2","Away player hoops scored 2","Peeling abbreviation 2","Home player name 3","Home player handicap 3","Home player hoops scored 3","Away player name 3","Away player handicap 3","Away player hoops scored 3","Peeling abbreviation 3","Home player name 4","Home player handicap 4","Home player hoops scored 4","Away player name 4","Away player handicap 4","Away player hoops scored 4","Peeling abbreviation 4"]:
                    	    print("Unexpected field", key, "in", jsonobj)
                    cordict[ts] = {key:val for key,val in cor.items() if key != 'ts'}
    return cordict

def readResults(results, cordict):
    ''' Read and correct the results. Each result record has a key of
    league, date, venue, home_team and away_team. If a game has been
    recorded twice then it should be found twice and is marked as a dual
    record. It is only stored the first time it is found.

    Returns: data - the data as a list of rows 
             dual - key of useful data that has been recorded just twice 

    '''
    with open(results, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        data = {}
        dual = {}
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
                   
                    one = {key:val  for key, val in row.items() if key not in ['Home team','Away team','League','Date','Venue','Email address','Email of opponents captain','Timestamp','More games to record?'] }
                    two = {key:val  for key, val in data[key].items() if key not in ['Home team','Away team','League','Date','Venue','Email address','Email of opponents captain','Timestamp','More games to record?'] }
                    if (row['Email address'].lower().strip() != data[key]['Email of opponents captain'].lower().strip()) or (row['Email of opponents captain'].lower().strip() != data[key]['Email address'].lower().strip()):
                        html = htmlKey(row)
                        html += htmlCaptains(row)
                        html += htmlCaptains(data[key])
                        html += htmlSign()
                        sendMail([row['Email address'],data[key]['Email address']],"Inconsistent captains for submitted results", html)
                    elif one != two:
                        looking = True
                        for i in range(1,5):
                            if not looking: break
                            for field in ['Home player hoops scored', 'Away player hoops scored','Home player name', 'Away player name', 'Home player handicap', 'Away player handicap', 'Peeling abbreviation']:
                                oneData = row[field + ' ' + str(i)]
                                twoData = data[key][field + ' ' + str(i)]
                                if oneData != twoData:
                                    html = htmlKey(row)
                                    html += "<p>" + field + " for game " + str(i) + " is recorded as " + oneData + " and as " + twoData + "</p>"
                                    html += htmlSign()
                                    sendMail([row['Email address'],data[key]['Email address']],"Inconsistent data for records", html)
                                    looking = False
                                    break
                        if looking:
                            print("\nProblem with " + textKey(row) + "\n" + str(one) + "\n" + str(two))
                    else:
                        dual[key] = True
                else:
                    keycount[key] += 1
                    del dual[key]
                    print ("Two many entries for", key)

    # Report other problems
    if cordict: print("Some corrections have not been applied", cordict)              

    for one in {key: val for key, val in keycount.items() if val == 1 }.keys():
        datum = data[one]
        html = "<p>" + "Games between " + one[3] + " and " + one[4] + " in " + one[0] + " league at " + one[2] + " on " + one[1] + " have only a single report submitted by " + datum["Email address"] +  " and which cited you as the opposing captain of the day. Please submit the corresponding report via https://forms.gle/Ta7p2ooKKzJjFBuB9 so that the result can be recorded.</p>"
        to = [datum["Email of opponents captain"]]
        sendMail(to, "Missing report", html)

    return data, dual

def htmlSign():
    return "<p>Please reconcile these differences and reply-all to this email with an explanation</p><p>Steve Fisher <em>(SCF AC Leagues Manager)</em></p>"

def htmlCaptains(row):
    e1 = row['Email address']
    e2 = row['Email of opponents captain']
    return "<p>Record with timestamp " + row['Timestamp'] + " shows self and opposing captain of the day as " + e1 + " and " + e2 +"</p>"

def textKey(row):
    '''Return textual representation of the records key'''
    return "Games between " + row['Home team'] + " and " + row['Away team'] + " in " + row['League'] + " league at " + row['Venue'] + " on " + row['Date']

def htmlKey(row): return "<p>" + textKey(row) + "</p>"

def getLeagues(captains):
    ''' Derive an array of leagues indexed by name from the captains csv
    file.

    Returns: leagues - an array of Leagues indexed by name

    '''   
    A = set()
    B = set()
    HN = set()
    HS = set()
    leagues = {}
    with open(captains, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            captain = Captain(row['Club'], row['Given'], row['Surname'], row['Email'])
            if row['A Level'] == "1": A.add(captain)
            if row['B Level'] == "1": B.add(captain)
            if row['Hcap N'] == "1": HN.add(captain)
            if row['Hcap S'] == "1": HS.add(captain)

    for name,league, game_count in zip(['A Level','B Level','Hcap N','Hcap S'],[A,B,HN,HS],[2,3,4,4]):
        leagues[name] = League(name, league, game_count)
    return leagues

def populateLeagues(data, dual, leagues):
    '''Populate the leagues.'''
    for d in dual:
        datum = data[d]
        date = datum["Date"]
        venue = datum["Venue"]
        league_name = d[0]
        league = leagues[league_name]
        h_team = d[3]
        a_team = d[4]
        to = [datum["Email address"],datum["Email of opponents captain"]]
        for i in range(1,5):
            if len(datum['Home player hoops scored ' + str(i)].strip()) == 0: break
            h_score = int(datum['Home player hoops scored ' + str(i)])
            a_score = int(datum['Away player hoops scored ' + str(i)])
            h_name = datum['Home player name ' + str(i)]
            a_name = datum['Away player name ' + str(i)]
            h_handicap = datum['Home player handicap ' + str(i)]
            a_handicap = datum['Away player handicap ' + str(i)]
            pa = datum['Peeling abbreviation ' + str(i)]
            league.record(h_team, h_name, h_handicap, h_score, a_team, a_name, a_handicap, a_score, pa, date, venue, to)

def sendMail(to, subject, html, report=False):
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
        print("\n\nTo: " + str(to) + "\nSubject: " + subject + "\n" + text)

    if (mailWanted and not report) or (reportWanted and report):
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = ",".join(to) if isinstance(to,list) else to
        message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))
                           
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("mail.southern-croquet.org.uk", 465, context=context) as server:
            server.login(username, password)
            server.sendmail(sender_email,to,message.as_string())
        
def main():
    ''' Main program. '''

    parser = argparse.ArgumentParser(description="Process SCF league results.")
    parser.add_argument("-m","--sendmail", action="store_true", help="send emails to those needing to fix something")
    parser.add_argument("-v","--verbose", action="store_true", help="list text version of emails that will be sent with -m selected")
    parser.add_argument("-c", "--configfile", default="default")
    parser.add_argument("-r", "--report", action="store_true", help="send email reports for ranking purposes")
    args = parser.parse_args()
    global mailWanted, printWanted, reportWanted
    mailWanted = args.sendmail
    printWanted = args.verbose
    reportWanted = args.report

    # Find the config file and read it
    captains, results, corrections = readConfig(args.configfile)
   
    # Read in the file of corrections
    cordict = getCordict(corrections)
    
    # Now read the results
    data, dual = readResults(results, cordict)

    # Find what matches should be played
    leagues = getLeagues(captains)
    
    # Now fill the league tales with "dual" results
    populateLeagues(data, dual, leagues)
              
    # Now produce tables
    for name in leagues:
         league = leagues[name]
         print (league)
         with open("tables/"+name+"_table.json",'w') as f:
             f.write(league.table())
         with open("tables/"+name+"_games.json",'w') as f:
             f.write(league.gamesTable())
         if name in ("A Level", "B Level"):
             league.reportResults()
    
if __name__ == '__main__': main()
