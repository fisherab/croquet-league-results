#!/usr/bin/env python
import csv
import sys
import configparser
import json

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

with open(results, newline='') as csvfile:
    reader = csv.DictReader(csvfile)

    data = {}
    dual = {}
    keycount = {}
    for row in reader:
        if row['Timestamp'] in cordict:
            print ("Should be fixed", cordict[row['Timestamp']], row)
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
                    print ("Inconsistent captains for", key, ":", row['Email address'], "and", data[key]['Email of opponents captain'])
                elif row['Email of opponents captain'] != data[key]['Email address']:
                    print ("Inconsistent captains for", key, ":", row['Email of opponents captain'], "and", data[key]['Email address'])
                elif one != two:
                    print ("Inconsistent data for", key, "reported by", row['Email address'], "and",  data[key]['Email address'])
                else:
                    dual[key] = True
            else:
                keycount[key] += 1
                del dual[key]
                print ("Two many entries for", key)
              
print ("Keycount", keycount)
print ("Dual", dual)
one = {key: val for key, val in keycount.items() if val == 1 }
print ("Ones", one)


