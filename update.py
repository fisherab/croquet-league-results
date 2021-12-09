#!/usr/bin/env python
import csv
import sys
import configparser
import json

class Captain:
    def __init__(self, team, given, surname, email):
        self.team = team
        self.given = given
        self.surname = surname
        self.email = email

    def __str__(self):
        return self.team + ": " + self.given + " " + self.surname + " <" + self.email +">"

class League:
    def __init__(self,name,captains, game_count, tpress_num):
        self.name = name
        self.captains = captains
        self.matches = {}
        for c1 in captains:
            for c2 in captains:
                if c1.team < c2.team:
                    self.matches[c1.team, c2.team] = []
        self.min_game_count = (game_count +2)//2
        self.tpress_num = tpress_num

    def __str__(self):
        p = "League:" + self.name
        completed = 0
        started = 0
        for m in self.matches:
            mc = len(self.matches[m])
            if mc >= self.min_game_count: completed += 1
            elif mc > 0: started += 1

        return p + ", Completed:" + str(completed) + ", Started:" + str(started) + ", Not started:" + str(len(self.matches) - completed - started) 
    
    def record(self, home_team, home_score, away_team, away_score):
        if home_score == away_score:
            print ("Attempt to record drawn game between ", home_team, "and", away_team, "in league", self.name)
        elif (home_team < away_team): 
            key=home_team, away_team
            if key in self.matches:
                self.matches[key].append((int(home_score),int(away_score)))
            else:
                print ("Attempt to record game between ", home_team, "and", away_team, "in league", self.name, "No match expected")
        else: 
            key=away_team, home_team
            if key in self.matches:
                self.matches[key].append((int(away_score), int(home_score)))
            else:
                print ("Attempt to record game between ", home_team, "and", away_team, "in league", self.name, "No match expected")
                
    def table(self):
        tdata = {}
        tdata['name'] = self.name
        tdata['data'] = []
        rows = tdata['data']
        
        for c1 in self.captains:
            row = []
            rows.append(row)
            row.append("Team")
            for c2 in self.captains:
                row.append(c2.team)
            row.extend(["Played","Pts"])
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
                        print(res)
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
                        print(res)
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
        
          
# Find the config file and read it
args = sys.argv[1:]
if len(args) == 1:
    configFile = args[0]
else:
    configFile = "default"

config=configparser.ConfigParser()
config.read(configFile + ".ini")
corrections = config.get("files","corrections")
results = config.get("files", "results")
captains = config.get("files", "captains")

# Read in the file of corrections
cordict = {}
with open(corrections) as clist:
    for jsonobj in clist:
        cor = json.loads("{" + jsonobj + "}")
        ts = cor["ts"]
        if ts in cordict:
            print ("Corrections file has multiple occurences of timestamp", ts)
        else:
            cordict[ts] = {key:val for key,val in cor.items() if key != 'ts'}

# Now read the results
with open(results, newline='') as csvfile:
    reader = csv.DictReader(csvfile)

    data = {}
    dual = {}
    keycount = {}
    for row in reader:
        ts = row['Timestamp']
        if ts in cordict:
            op = cordict[row['Timestamp']]['op']
            if op == "update":
                updates = {key:val for key,val in cordict[row['Timestamp']].items() if key != 'op'}
                for key, val in updates.items():
                    row[key]=val
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
               
                one = {key:val  for key, val in row.items() if key not in ['Home team','Away team','League','Date','Venue','Email address','Email of opponents captain','Timestamp'] }
                two = {key:val  for key, val in data[key].items() if key not in ['Home team','Away team','League','Date','Venue','Email address','Email of opponents captain','Timestamp'] }
                if row['Email address'] != data[key]['Email of opponents captain']:
                    print ("Inconsistent captains for records",  row['Timestamp'], "and",  data[key]['Timestamp'])
                elif row['Email of opponents captain'] != data[key]['Email address']:
                    print ("Inconsistent captains for records",   row['Timestamp'], "and",  data[key]['Timestamp'])
                elif one != two:
                    print ("Inconsistent data for records", row['Timestamp'], "and",  data[key]['Timestamp'])
                else:
                    dual[key] = True
            else:
                keycount[key] += 1
                del dual[key]
                print ("Two many entries for", key)

# Report other problems
if cordict: print("Some corrections have not been applied", cordict)              

for one in {key: val for key, val in keycount.items() if val == 1 }.keys():
    print (one, "has only a single report")

# Find what matches should be played
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

for name,league, game_count, tpress_num in zip(['A Level','B Level','Hcap N','Hcap S'],[A,B,HN,HS],[2,3,4,4],[3,4,5,6]):
    leagues[name] = League(name, league, game_count, tpress_num)

# Now find game results to report and match results
for d in dual:
    datum = data[d]
    print ("Result to be stored", datum)
    for i in range(1,5):
        h = datum['Home player hoops scored ' + str(i)]
        a = datum['Away player hoops scored ' + str(i)]
        if len(h.strip()) == 0: break
        league_name = d[0]
        league = leagues[league_name]
        home_team = d[3]
        away_team = d[4]
        league.record(home_team, h, away_team, a)
        
# Now produce tables
for name in leagues:
     league = leagues[name]
     print (league)
     with open("tables/"+name+"_table.json",'w') as f:
         f.write(league.table())
    
league = leagues["Hcap N"]


print(leagues["Hcap N"].table())

