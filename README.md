# RIFTEHR

Relationship Inference From The EHR (RIFTEHR) is an automated algorithm for identifying relatedness between patients in an institution's Electronic Health Records.

Original Authors: Fernanda Polubriaginof and Nicholas Tatonetti

2nd Version: Farhad Ghamsari

This Version: Colby Wood and Dan Turner

http://riftehr.tatonettilab.org

Remember to always respect patient privacy.

---
## What is different about this version?

2nd ver.: Fully Python, no dependencies on SQL or Julia
<br>2nd ver.:  Much, much faster, thanks to vectorization of functions
<br>Changes in the current version:
- New Step 2 replace old Steps 2, 3, and 4.
- Conflict checks (spouse age, generation age, flipped relationship, mismatched provided relationships) are now fully integrated into the inference step at every stage
- Families are now defined by networkx before inferences are made and the inference step is applied within families instead of across the entire dataset
- Two-person families now skip the inference step
- Lookup dictionaries are used in place of if/else statements whenever possible 
- List/dictionary comprehensions are used in place of for loops whenever possible
- The inference step is now about 60 times faster than in the 2nd version

## Setting up your files
<b>Patient Demographics Table</b> is a comma delimited file with the following headers. Each of these values corresponds to the patient:

    - MRN, FirstName, LastName, PhoneNumber, Zipcode

<b>Emergency Contacts Table</b> is a comma delimited file with the following headers. MRN_1 corresponds to the MRN of the patient. (It is the link to the Patient Demographics Table.)
The rest of the values correspond to the Patient's Emergency Contact.
EC_Relationship refers to the relationship between Patient and EC. (If EC_Relationship is Parent, then the EC is the Patient's Parent.) 

    - MRN_1, EC_LastName, EC_FirstName, EC_PhoneNumber, EC_Zipcode, EC_Relationship

## Customization
- Go to Step 0 > `preprocess.py` > `process_phones()`:
    - Remove any additional phone numbers that are recurrent in your data set. For example, our team had to remove the Northwestern University main line as it was a common placeholder for emergency contact's phone numbers.
- See `relation_map.csv`. The input_relation column contains emergency contact relationships as they appear in your dataset, and the output_relations column is what they should map to, as required by the RIFTEHR program.
- In Step 1 > `match_in_batches.py` > `find_matches()` I felt that searching by a single data element for a possible match was too nonspecific, and opted to leave it commented out. You may experiment with it by uncommenting the section.

## Contact
Should you have any questions, comments, suggestions, please don't hesitate to reach out:

Ver. 2: fghamsari@tulane.edu  Current Ver.: colby.witherup@northwestern.edu
