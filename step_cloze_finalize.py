# This is the final step in step-cloze grading
import os, sys, json, re
import batch_utils

CRITIC_MODEL = "o3-2025-04-16"

assert len(sys.argv) == 3, "Usage: <testname> <batchid>"
testname = sys.argv[1]
batchid = sys.argv[2] # This is an ID used by the server API (e.g. OpenAI's API)

# Do the download from the server to a local file
download_file = batch_utils.DIR_BATCH_DOWNLOADS + testname + batch_utils.POSTFIX_DOWNLOAD2 + ".jsonl"
if os.path.exists(download_file):
    print("NOTE: The following file already exists:", download_file)
batch_utils.download_response(batchid, download_file, CRITIC_MODEL)

# Open the downloaded file
download_data = []
with open(download_file, "r") as f:
    for line in f.readlines():
        download_data.append(json.loads(line))

# Run through the output
total_input_tokens = 0
total_reasoning_tokens = 0
total_output_tokens = 0
dict_histogram = {"0": 0, "1":0, "2":0, "3":0, "unknown":0}
for response_datum in download_data:
    assert response_datum["error"] == None
    total_input_tokens += response_datum["response"]["body"]["usage"]["prompt_tokens"]
    total_reasoning_tokens += response_datum["response"]["body"]["usage"]["completion_tokens_details"]["reasoning_tokens"]
    total_output_tokens += response_datum["response"]["body"]["usage"]["completion_tokens"]
    id = response_datum["custom_id"]
    assert len(response_datum["response"]["body"]["choices"]) == 1
    assert response_datum["response"]["body"]["choices"][0]["message"]["role"] == "assistant"
    response = response_datum["response"]["body"]["choices"][0]["message"]["content"]

    # Analyze it, taking the rightmost instance of one of the acceptable numbers
    matches = list(re.finditer("[0-3]", response))
    if len(matches) == 0:
        result = "unknown"
        print("WARNING: Unknown answer")
    else:
        result = matches[-1].group()

    print(id, "\t", response, "\t", result)
    dict_histogram[result] += 1

# Here is useful information for keeping track of costs
print("total_input_tokens =", total_input_tokens)
print("total_reasoning_tokens =", total_reasoning_tokens)
print("total_output_tokens = ", total_output_tokens)
print("TOTAL DOWNLOADED=", len(download_data))

print("HISTOGRAM:", dict_histogram)