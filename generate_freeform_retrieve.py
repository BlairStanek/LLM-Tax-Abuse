# Simple file that retrieves files from batches kicked off by generate_freeform.py
import os, sys
import batch_utils

assert len(sys.argv) == 4, "Usage: <testname> <model> <batchid>"
testname = sys.argv[1]
model = sys.argv[2]
batchid = sys.argv[3] # This is an ID used by the server API (e.g. OpenAI's API)

# Do the download from the server to a local file
download_file = batch_utils.DIR_BATCH_DOWNLOADS + testname + batch_utils.POSTFIX_DOWNLOAD1 + ".jsonl"
if os.path.exists(download_file):
    print("NOTE: The following file already exists:", download_file)
batch_utils.download_response(batchid, download_file, model)
print("Output at:", download_file)