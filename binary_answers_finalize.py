# This is used as the third (and final) step of analysis_verification or goal_verification_*
# Call it with the testname (e.g. analysis_verification_1_gpt-4.1-nano-2025-04-14_2025-07-25at14_50_12),
# model (e.g. o3), and batchid (e.g. batch_6883d1e653648190b2899232c2511603) to
# have it upload a batch to clarify binary answers.
import os, sys
import batch_utils

assert len(sys.argv) == 4, "Usage: <testname> <model> <batchid>"
testname = sys.argv[1]
model = sys.argv[2]
batchid = sys.argv[3] # This is an ID used by the server API (e.g. OpenAI's API)

# Do the download from the server to a local file
download_file = batch_utils.DIR_BATCH_DOWNLOADS + testname + batch_utils.POSTFIX_DOWNLOAD2 + ".jsonl"
if os.path.exists(download_file):
    print("NOTE: The following file already exists:", download_file)
batch_utils.download_response(batchid, download_file, model)

list_ids_responses, total_input_tokens, total_reasoning_tokens, total_output_tokens = \
    batch_utils.extract_response(download_file, model) # does much of the work

# Here is useful information for keeping track of costs
print("total_input_tokens =", total_input_tokens)
print("total_reasoning_tokens =", total_reasoning_tokens)
print("total_output_tokens = ", total_output_tokens)

total_responses = 0
total_yes_responses = 0
total_unknown_responses = 0
dict_strategies = {} # used to count number of strategies
for id, response in list_ids_responses:
    print(id, "\t", response)

    # Figure out which strategy this belongs to
    assert len(id.split("_")) > 1
    assert id.split("_")[0] == "Strategy"
    strategy_num = id.split("_")[1]
    if strategy_num not in dict_strategies:
        dict_strategies[strategy_num] = None

    # process and count this answer
    total_responses += 1
    stripped_response = response.strip().strip(".*").lower()  # the * is stripped since LLMs may try to bold the answer
    if stripped_response.startswith("yes"):
        total_yes_responses += 1
    elif stripped_response.startswith("no"):
        dict_strategies[strategy_num] = "no"
    else:
        dict_strategies[strategy_num] = "unknown"
        total_unknown_responses += 1

print("Strategies all Yeses:")
[print(x[0]) for x in dict_strategies.items() if x[1] is None]


print("Raw total_responses=        ", total_responses)
print("Raw total_yes_responses=    ", total_yes_responses)
print("Raw total_unknown_responses=", total_unknown_responses)

print("Num Strategies =", len(list(dict_strategies.keys())))
print("Num Strategies All Yeses   =", len([x[0] for x in list(dict_strategies.items()) if x[1] is None]))
