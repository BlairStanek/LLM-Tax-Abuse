import os, sys, re
import batch_utils, utils
from scipy.stats import spearmanr

assert len(sys.argv) == 4, "Usage: <testname> <model> <batchid>"
testname = sys.argv[1]
model = sys.argv[2]
batchid = sys.argv[3] # This is an ID used by the server API (e.g. OpenAI's API)

# Do the download from the server to a local file
download_file = batch_utils.DIR_BATCH_DOWNLOADS + testname + batch_utils.POSTFIX_DOWNLOAD1 + ".jsonl"
if os.path.exists(download_file):
    print("NOTE: The following file already exists:", download_file)
batch_utils.download_response(batchid, download_file, model)

list_ids_responses, total_input_tokens, total_reasoning_tokens, total_output_tokens = \
    batch_utils.extract_response(download_file, model) # does much of the work

# First index is the ACTUAL, and second index is PREDICTED
dict_confusion_matrix = {
    "3": {"3": 0, "2": 0, "1": 0, "0": 0},
    "2": {"3": 0, "2": 0, "1": 0, "0": 0},
    "1": {"3": 0, "2": 0, "1": 0, "0": 0},
    "0": {"3": 0, "2": 0, "1": 0, "0": 0}
}

dict_total_human_grades = {"3": 0, "2": 0, "1": 0, "0": 0}
dict_total_model_grades = {"3": 0, "2": 0, "1": 0, "0": 0}

print("| HUMAN GRADE | MODEL GRADE |")

total_raw_human_grades = 0
total_raw_model_grades = 0
num_grades_equal = 0
num_human_higher = 0
num_model_higher = 0

human_grades = []
model_grades = []

for id, response in list_ids_responses:
    origin_filename = utils.FREEFORM_DIR + "/" + id
    if not origin_filename.endswith(".txt"):
        origin_filename += ".txt"
    with open(origin_filename, "r") as f:
        freeform_str = f.read()
    first_line = freeform_str.split("\n")[0].strip()
    assert first_line.startswith("Grade=")
    human_grade = first_line[len("Grade="):]
    assert human_grade in ["0", "1", "2", "3"]
    dict_total_human_grades[human_grade] += 1

    matches = list(re.finditer("[0-3]", response))
    assert len(matches) > 0
    model_grade = matches[-1].group()
    dict_total_model_grades[model_grade] += 1

    dict_confusion_matrix[human_grade][model_grade] += 1

    print("| ", human_grade, "         | ", model_grade , "         |\n")
    total_raw_human_grades += int(human_grade)
    total_raw_model_grades += int(model_grade)
    if int(human_grade) == int(model_grade):
        num_grades_equal += 1
    elif int(human_grade) > int(model_grade):
        num_human_higher += 1
    else:
        num_model_higher += 1

    human_grades.append(int(human_grade))
    model_grades.append(int(model_grade))

print("| HUMAN GRADE | MODEL GRADE |\n")

print("average human grade: ", total_raw_human_grades /float(len(list_ids_responses)))
print("average model grade: ", total_raw_model_grades /float(len(list_ids_responses)))
print("num_grades_equal=",num_grades_equal)
print("num_human_higher =", num_human_higher)
print("num_model_higher =", num_model_higher)


rho, p_value = spearmanr(human_grades, model_grades)

print(f"Spearman's rho: {rho}")
print(f"P-value: {p_value}")

# Here is useful information for keeping track of costs
print("argv=", sys.argv[1:])
print("total_input_tokens =", total_input_tokens)
print("total_reasoning_tokens =", total_reasoning_tokens)
print("total_output_tokens = ", total_output_tokens)


print("Confusion Matrix (columns from model):")
for human_grade in ["top_row", "3", "2", "1", "0"]:
    if human_grade == "top_row":
        print("         | 3 | 2 | 1 | 0 |")
    else:
        print("human", human_grade, end="  ")
        for model_grade in ["3", "2", "1", "0"]:
            print("|{:2d} ".format(dict_confusion_matrix[human_grade][model_grade]), end="")
        print("|") # , sum(dict_confusion_matrix[human_grade].values()))

for human_grade in ["3", "2", "1", "0"]:
    print("[", end="")
    for model_grade in ["3", "2", "1", "0"]:
        print(dict_confusion_matrix[human_grade][model_grade], end="")
        if model_grade != "0":
            print(", ", end="")
    print("]", end="")
    if human_grade != "0":
        print(", ")

print("\ntotal human grades:", dict_total_human_grades, sum(dict_total_human_grades.values()))
print("total model grades:", dict_total_model_grades, sum(dict_total_model_grades.values()))
