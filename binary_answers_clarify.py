# This is used as the second step of analysis_verification or goal_verification_*
# Call it with the testname (e.g. analysis_verification_1_gpt-4.1-nano-2025-04-14_2025-07-25at14_50_12),
# model (e.g. o3), and batchid (e.g. batch_6883d1e653648190b2899232c2511603) to
# have it upload a batch to clarify binary answers.
import os, sys, json
import batch_utils

assert len(sys.argv) == 4, "Usage: <testname> <model> <batchid>"
testname = sys.argv[1]
model = sys.argv[2]
batchid = sys.argv[3] # This is an ID used by the server API (e.g. OpenAI's API)

# If the response format does not have it, then open the file that was uploaded
# to get this request, as we need this to build the next call
if batch_utils.is_claude(model) or batch_utils.is_openai(model):
    uploaded_file = batch_utils.DIR_BATCH_UPLOADS + testname + batch_utils.POSTFIX_UPLOAD1 + ".jsonl"
    assert os.path.exists(uploaded_file), "ensure original file present"
    input_data = []
    with open(uploaded_file, "r") as f:
        for line in f.readlines():
            input_data.append(json.loads(line))

# Do the download from the server to a local file
download_file = batch_utils.DIR_BATCH_DOWNLOADS + testname + batch_utils.POSTFIX_DOWNLOAD1 + ".jsonl"
if os.path.exists(download_file):
    print("NOTE: The following file already exists:", download_file)
batch_utils.download_response(batchid, download_file, model)

# Open the downloaded file
response_data = []
with open(download_file, "r") as f:
    for line in f.readlines():
        response_data.append(json.loads(line))

if batch_utils.is_google(model):
    input_data = None
else:
    assert len(input_data) == len(response_data)

list_ids_prompt1_response_prompt2, total_input_tokens, \
    total_reasoning_tokens, total_output_tokens = \
    batch_utils.merge_input_response(input_data,
                                     response_data,
                                     model,
                                     "So the answer (just Yes or No) is:")

# Here is useful information for keeping track of costs
print("total_input_tokens =", total_input_tokens)
print("total_reasoning_tokens =", total_reasoning_tokens)
print("total_output_tokens = ", total_output_tokens)

# Write the files to get the clarifications and make the call
batch_filename = batch_utils.write_batch_file(testname,
                                              batch_utils.POSTFIX_UPLOAD2,
                                              model,
                                              list_ids_prompt1_response_prompt2)
batch_utils.upload_file_and_start(batch_filename, model)
