# This is the second part of step-cloze, in which we call to get a grade on the answer.
# We always use o3 as the critic model.
import os, sys, json
import batch_utils, utils

CRITIC_MODEL = "o3-2025-04-16"

assert len(sys.argv) == 4, "Usage: <testname> <original-model> <batchid>"
testname = sys.argv[1]
original_model = sys.argv[2]
batchid = sys.argv[3] # This is an ID used by the server API (e.g. OpenAI's API)

download_file = batch_utils.DIR_BATCH_DOWNLOADS + testname + batch_utils.POSTFIX_DOWNLOAD1 + ".jsonl"
if os.path.exists(download_file):
    print("NOTE: The following file already exists:", download_file)
batch_utils.download_response(batchid, download_file, original_model)

# Open the downloaded file
download_data = []
with open(download_file, "r") as f:
    for line in f.readlines():
        download_data.append(json.loads(line))

# Run through the output, building up the input
total_input_tokens = 0
total_reasoning_tokens = 0
total_output_tokens = 0
list_ids_prompts = [] # will be passed to call for grading
for response_datum in download_data:
    line_to_grade = None
    id = None
    if batch_utils.is_openai(original_model):
        assert response_datum["error"] == None
        total_input_tokens += response_datum["response"]["body"]["usage"]["prompt_tokens"]
        total_reasoning_tokens += response_datum["response"]["body"]["usage"]["completion_tokens_details"]["reasoning_tokens"]
        total_output_tokens += response_datum["response"]["body"]["usage"]["completion_tokens"]
        id = response_datum["custom_id"]
        assert len(response_datum["response"]["body"]["choices"]) == 1
        assert response_datum["response"]["body"]["choices"][0]["message"]["role"] == "assistant"
        line_to_grade = response_datum["response"]["body"]["choices"][0]["message"]["content"]
    elif batch_utils.is_claude(original_model):
        assert response_datum["result"]["type"] == "succeeded"
        total_input_tokens += response_datum["result"]["message"]["usage"]["input_tokens"]
        total_output_tokens += response_datum["result"]["message"]["usage"]["output_tokens"]
        id = response_datum["custom_id"]

        for content in response_datum["result"]["message"]["content"]:
            if content["type"] == "text":  # other type includes "thinking"
                assert line_to_grade == None, "should be only one"
                line_to_grade = content["text"]
    elif batch_utils.is_google(original_model):
        id = response_datum["key"]

        assert len(response_datum["response"]["candidates"]) == 1
        assert response_datum["response"]["candidates"][0]["finishReason"] == "STOP"

        total_input_tokens += response_datum["response"]["usageMetadata"]["promptTokenCount"]
        total_output_tokens += response_datum["response"]["usageMetadata"]["candidatesTokenCount"]

        assert len(response_datum["response"]["candidates"][0]["content"]["parts"]) == 1
        line_to_grade = response_datum["response"]["candidates"][0]["content"]["parts"][0]["text"]

    else:
        assert False, "not implemented"

    if line_to_grade == None:
        print("ERROR: no line to grade", id)
        line_to_grade = "**HAD ERROR**"
    line_to_grade = line_to_grade.strip()
    if line_to_grade.lower().startswith("answer:"):
        line_to_grade = line_to_grade[len("answer:"):].strip()
    elif line_to_grade.lower().startswith("answer"):
        line_to_grade = line_to_grade[len("answer"):].strip()
    if len(line_to_grade.split("\n")) > 1:
        print("WARNING: Answer was too long: ", line_to_grade)
        if len(line_to_grade.split("\n")[0]) > len(line_to_grade.split("\n")[1]):
            line_to_grade = line_to_grade.split("\n")[0].strip() # choose longest of the first two lines
        else:
            line_to_grade = line_to_grade.split("\n")[1].strip()

    f_grading = open("few_shot_step_grading.txt", "r")  # This file is a key component
    user_prompt = f_grading.read()
    correct_and_to_grade = "CORRECT ANSWER: "
    correct_and_to_grade += utils.get_strategy_step_by_str(id)
    correct_and_to_grade += "\nANSWER TO GRADE: "
    correct_and_to_grade += line_to_grade
    print(id, "\n", correct_and_to_grade)
    user_prompt += correct_and_to_grade
    user_prompt += "\nWhat grade do you give this answer (3, 2, 1, or 0)?  Do **not** show your analysis.  " + \
        "Answer with **only** one of the numbers 3, 2, 1 or 0."

    list_ids_prompts.append((id, user_prompt))

# Here is useful information for keeping track of costs
print("total_input_tokens =", total_input_tokens)
print("total_reasoning_tokens =", total_reasoning_tokens)
print("total_output_tokens = ", total_output_tokens)
print("TOTAL ITEMS IN=", len(download_data), "TOTAL ITEMS OUT=", len(list_ids_prompts))

# Write the files to get the clarifications and make the call
batch_filename = batch_utils.write_batch_file(testname,
                                              batch_utils.POSTFIX_UPLOAD2,
                                              CRITIC_MODEL,
                                              list_ids_prompts)
batch_utils.upload_file_and_start(batch_filename, CRITIC_MODEL)

