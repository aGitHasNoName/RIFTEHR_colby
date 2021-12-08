"""
"""

from networkx import from_pandas_edgelist
from networkx import connected_components
from networkx import number_of_selfloops
import pandas as pd
import numpy as np
from itertools import permutations
from collections import defaultdict
import json
import time


#Load all lookup dictionaries
with open("Step2_InferenceAndConflicts/infer_dict.json", "r") as f:
    infer_dict = json.load(f)
with open("Step2_InferenceAndConflicts/opp_lookup.json", "r") as f:
    opp_lookup = json.load(f)
with open("Step2_InferenceAndConflicts/age_lookup.json", "r") as f:
    age_lookup = json.load(f)
with open("Step2_InferenceAndConflicts/flip_lookup.json", "r") as f:
    flip_lookup = json.load(f)
with open("Step2_InferenceAndConflicts/conflict_type_dict.json", "r") as f:
    conflict_type_dict = json.load(f)
with open("Step2_InferenceAndConflicts/female_rel_dict.json", "r") as f:
    female_rel_dict = json.load(f)
with open("Step2_InferenceAndConflicts/male_rel_dict.json", "r") as f:
    male_rel_dict = json.load(f)
flip_lookup_older = ["parent", "grandparent"]
flip_lookup_younger = ["child", "grandchild"]

#Define conflict check booleans - all booleans return the conflicts
def age_spouse_boolean(p, r, rel):
    try:
        return rel == "spouse" and (demo_dict[p][0] < 17 or demo_dict[r][0] < 17)
    except KeyError:
        return False
def age_parent_boolean(p, r, rel):
    try:
        return abs(demo_dict[p][0] - demo_dict[r][0]) < age_lookup[rel]
    except KeyError:
        return False
def provided_conflict_boolean(p, r, rel):
    try:
        return p in matches[r].keys() and rel != opp_lookup[matches[r][p][0][0]]
    except KeyError:
        return False
def flipped_conflict_boolean(p, r, rel):
    try:
        return (rel in flip_lookup_younger and demo_dict[p][0] < demo_dict[r][0]) or (rel in flip_lookup_older and demo_dict[p][0] > demo_dict[r][0])
    except KeyError:
        return False
def duplicate_provided_conflict_boolean(d):
    return [len([i[1] for i in v]) for v in d.values()] != [len(set([i[1] for i in v])) for v in d.values()]

#Define conflict-handling functions
def handle_duplicate_provided(d, fam):
    for p, v in d.items():
            i_dict = {}
            for i in v:
                if i[1] not in i_dict.keys():
                    i_dict[i[1]] = i[0]
                elif i[0] != i_dict[i[1]]:
                    conflict_list.append((str(fam), p, i[1], i[0], str(0), conflict_type_dict["dup_provided"]))
                    matches[p].pop(i[1])
                    if len(matches[p]) == 0:
                        matches.pop(p)
                    conflict_list.append((str(fam), p, i[1], i_dict[i[1]], str(0), conflict_type_dict["dup_provided"]))
def remove_provided_conflict_from_matches(fam, p, r, rel, loop, conflict_type):
    conflict_list.append((str(fam), p, r, rel, str(loop), conflict_type_dict[conflict_type]))
    matches[p].pop(r)
    if len(matches[p]) == 0:
        matches.pop(p)
        
#define function to create gendered relationship based on sex
def gendered_rel(r, rel):
    #this is handled in a function instead of a lookup dict because
    #I want to label any unexpected or missing sex data as original relation
    if demo_dict[r][1] == "F":
        try:
            return female_rel_dict[rel]
        except KeyError:
            return rel
    elif demo_dict[r][1] == "M":
        try:
            return male_rel_dict[rel]
        except KeyError:
            return rel
    else:
        return rel

def infer_check(family):
    conflict_families = []
    no_conflict_families = []
    family_conflict = False
    global conflict_list
    conflict_list = []
    famID = family[0]
    
    #create family dictionary
    family_dict = {p: v for p,v in matches_dict.items() if p in family[1]}
    global matches
    matches = {p: {x[1]: [(x[0], 0)] for x in v} for p,v in family_dict.items()}
    
    #CHECK for multiple relationships provided for same relation
    if duplicate_provided_conflict_boolean(family_dict):
        handle_duplicate_provided(family_dict, famID)
    
    #CHECK for age conflicts in provided relationships
    for p, r in list(permutations(family[1], 2)):
        try:
            #is there a provided relationship?
            provided_rel = matches[p][r][0][0]
            #remove provided spouse relationship if either spouse is under 17:
            if age_spouse_boolean(p, r, provided_rel):
                remove_provided_conflict_from_matches(famID, p, r, provided_rel, 0, "age_spouse_provided")
            #remove parent/child with <10 year difference, gp/gc <20, etc.
            elif age_parent_boolean(p, r, provided_rel):
                remove_provided_conflict_from_matches(famID, p, r, provided_rel, 0, "age_parent_provided")
            #flip provided age conflicts if parent is younger than child, gp younger than gc, etc.
            elif flipped_conflict_boolean(p, r, provided_rel):
                matches[p][r][0] = (flip_lookup[provided_rel], 0)
                #per Amy, decided to not flag flipped relationships in final output
                conflict_list.append((str(famID), p, r, provided_rel, str(0), conflict_type_dict["flip_parent"]))
        except KeyError:
            pass  
    
    #CHECK for provided conflicts - two people identify each other but relationships aren't opposite
    #this is separate because if there is an age conflict, we still want the second relationship    
    for p, r in list(permutations(family[1], 2)):
        try:
            provided_rel = matches[p][r][0][0]
            if provided_conflict_boolean(p, r, provided_rel):
                remove_provided_conflict_from_matches(famID, p, r, provided_rel, 0, "provided")
                remove_provided_conflict_from_matches(famID, r, p, matches[r][p][0][0], 0, "provided")
        except KeyError:
            pass
    
    #Create opposite matches:
    for i in list(permutations(family[1], 2)):
        try:
            opp_rel = opp_lookup[matches[i[0]][i[1]][0][0]]
            if i[1] not in matches.keys():
                matches[i[1]] = {i[0]: [(opp_rel, .5)]}
            elif i[0] not in matches[i[1]].keys():
                matches[i[1]][i[0]] = [(opp_rel, .5)]
            elif matches[i[1]][i[0]][0][0] == opp_rel:
                pass
        except KeyError:
            pass
    
    #If family has more than two relationships remaining, infer new relationships
    if len(matches.keys()) > 2:
        combos = list(permutations(family[1], 3))
        b = 0
        check = True
        while check:
            a = 0
            b += 1
            for com in combos:
                try:
                    
                    #create new relationship
                    new_rel = infer_dict[matches[com[0]][com[1]][0][0]][matches[com[1]][com[2]][0][0]]
                    
                    #CHECK if the new relationship is spouse, are both parties over 16?
                    if age_spouse_boolean(com[0], com[2], new_rel):
                        conflict_list.append((str(famID), com[0], com[2], new_rel, str(b), conflict_type_dict["age_spouse"]))
                        family_conflict = True
                    
                    #CHECK if the new relationship is x-parent, is there at least a 10-year gap per generation?
                    elif age_parent_boolean(com[0], com[2], new_rel):
                        conflict_list.append((str(famID), com[0], com[2], new_rel, str(b), conflict_type_dict["age_parent"]))
                        family_conflict = True
                    
                    #ready to add the relationship
                    else:
                        
                        #this is a brand new relationship
                        if com[2] not in matches[com[0]].keys():
                            matches[com[0]][com[2]] = [(new_rel, b)]
                        
                        #this exact relationship already exists
                        elif new_rel == matches[com[0]][com[2]][0][0]:
                            pass
                        
                        #there is a less specific relationship than already exists
                        elif new_rel in matches[com[0]][com[2]][0][0].split("_"):
                            matches[com[0]][com[2]][0] = (new_rel, b)
                        
                        #there is a more specific relationship that already exists
                        elif matches[com[0]][com[2]][0][0] in new_rel.split("_"):
                            pass
                        
                        #CHECK there is a conflict with a relationship that already exists
                        else:    
                            matches[com[0]][com[2]].append((new_rel, b))
                            conflict_list.append((str(famID), com[0], com[2], new_rel, str(b), conflict_type_dict["inferred"]))
                            family_conflict = True
                            
                    combos.remove(com)
                    a +=1
                
                #there isn't a third party relationship on this pass, but there might be later
                except KeyError:
                    pass
            
            #there were no new inferred relationships on this pass, so all possible inferences have been made
            if a == 0:
                check = False
    
    #add data to final lists
    if len(conflict_list) > 0:
        for i in conflict_list:
            conflict_families.append((i[0], i[1], i[3], i[2], i[4], gendered_rel(i[2], i[3]), str(demo_dict[i[1]][0]), str(demo_dict[i[2]][0]), str(demo_dict[i[1]][1]), str(demo_dict[i[2]][1]), i[5]))

    if family_conflict == False:
        for p,v in matches.items():
            for r, tup_list in v.items():
                for tup in tup_list:
                    no_conflict_families.append((str(famID), p, tup[0], r, str(tup[1]), gendered_rel(r, tup[0]), str(demo_dict[p][0]), str(demo_dict[r][0]), str(demo_dict[p][1]), str(demo_dict[r][1])))
    else:     
        for p,v in matches.items():
            for r, tup_list in v.items():
                for tup in tup_list:
                    conflict_families.append((str(famID), p, tup[0], r, str(tup[1]), gendered_rel(r, tup[0]), str(demo_dict[p][0]), str(demo_dict[r][0]), str(demo_dict[p][1]), str(demo_dict[r][1]), "no_primary_conflict"))
                        
    return conflict_families, no_conflict_families

def step_two(df, patient_info_file, ec_info_file):
    #Load all data and convert to dictionaries
    demo_pt_df = pd.read_csv(patient_info_file, dtype=str)#.replace(np.nan, '')
    demo_ec_df = pd.read_csv(ec_info_file, dtype=str)#.replace(np.nan, '')
    #print(f"pt column names: {demo_pt_df.columns}")
    #print(f"ec column names: {demo_ec_df.columns}")
    demo_dict_pt = {mrn: (float(age), sex) for mrn, age, sex in zip(demo_pt_df["MRN"], demo_pt_df["Age"], demo_pt_df["Sex"])}
    demo_dict_ec = {mrn: (float(age), sex) for mrn, age, sex in zip(demo_ec_df["MRN_1"], demo_ec_df["Age"], demo_ec_df["Sex"])}
    global demo_dict
    demo_dict = {**demo_dict_ec, **demo_dict_pt}
    global matches_dict
    matches_dict = defaultdict(list)
    for index, row in df.iterrows():
        if row['pt_mrn'] != row['matched_mrn']:
            matches_dict[str(row['pt_mrn'])].append((row['ec_relation'], str(row['matched_mrn'])))
    
    #Create families
    F = from_pandas_edgelist(df, "pt_mrn", "matched_mrn")
    c = [s for s in connected_components(F) if len(s) > 1]
    
    #Check for self-matches
    if number_of_selfloops(F) > 0:
        print(f"{number_of_selfloops(F)} self matches.")
    
    #Sort families largest to smallest
    c.sort(key=len, reverse=True)
    
    #assign family IDs
    c_dict = {i:list(fam) for i, fam in zip(range(1, len(c)+1), c)}

    #Run conflict checks and inferences and format output
    time_step1 = time.time()
    results = [infer_check(x) for x in c_dict.items()]
    time_step2 = time.time()
    print("Time Taken for inference: ", time_step2 - time_step1)
    nc_families = [i for f in results for i in f[1]]
    final_nc_families = [("famID", "pt_mrn", "ec_relation", "matched_mrn", "inference_pass", "specific_relation", "pt_age", "matched_age", "pt_sex", "matched_sex")] + nc_families
    c_families = [i for f in results for i in f[0]]
    final_c_families = [("famID", "pt_mrn", "ec_relation", "matched_mrn", "inference_pass", "specific_relation", "pt_age", "matched_age", "pt_sex", "matched_sex", "conflict_type")] + c_families

    return final_c_families, final_nc_families
    