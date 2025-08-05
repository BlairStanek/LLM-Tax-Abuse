# Has the models free-form grade
import argparse, copy, os
import call_utils, utils, batch_utils

parser = argparse.ArgumentParser(
    description='Has a model grade the free-form output of another model')
parser.add_argument('--file', required=False,
                    help='used on a single file')
parser.add_argument('--model', required=True,
                    help='which LLM to call or prepare to call')
args = parser.parse_args()
call_utils.log_arbitrary("freeform_grade, with args=" + str(args))

list_ids_prompts = []
for filename in os.listdir(utils.FREEFORM_DIR):
    if args.file is None or filename == args.file:
        with open(utils.FREEFORM_DIR + "/" + filename, "r") as f:
            freeform_str = f.read()

        prompt_str = "You will be grading a U.S. tax-law strategy that a student came up with.  " + \
            "The student was given tax-law authorities to use, background facts, and one or more " + \
            "goals the strategy must achieve.\n\n"

        freeform_lines = freeform_str.split("\n")
        assert freeform_lines[0].startswith("Grade=")
        grade = freeform_lines[0][len("Grade="):].strip()
        assert grade in ["0", "1", "2", "3"]
        assert freeform_lines[1].startswith("Notes=")
        assert freeform_lines[2].startswith("202") # start of a year
        assert freeform_lines[3].startswith("generate_strategy()")
        assert freeform_lines[4] == "****** user"
        assert freeform_lines[5].startswith("You will be coming up with a tax strategy")
        assert freeform_lines[6].strip() == ""
        assert freeform_lines[7] == "Here are the authorities you will be applying:"
        subset_freeform = "Here are the tax-law authorities:\n" + \
                          "\n".join(freeform_lines[8:])

        subset_freeform = subset_freeform.replace("****** assistant",
                                "\n=== BELOW IS THE STUDENT'S ANSWER: ===\n")

        prompt_str += subset_freeform.rstrip() + "\n=== END OF THE STUDENT'S ANSWER ===\n\n"
        prompt_str += "=== YOUR TASK: ===\n\n"

        with open("freeform_grade_rubric.txt", "r") as f:
            rubric_str = f.read()
        prompt_str += rubric_str

        print(prompt_str)

        assert filename.endswith(".txt")
        filename_stripped = filename[:-len(".txt")]

        list_ids_prompts.append((filename_stripped, prompt_str))

if args.file is None:
    testname = batch_utils.get_testname("freeform_grade", args.model)
else:
    filename_stripped = args.file
    assert args.file.endswith(".txt")
    filename_stripped = filename_stripped[:-len(".txt")]
    testname = batch_utils.get_testname("freeform_grade_" + filename_stripped, args.model)
print("args=", args)
print("testname=", testname)
batch_filename = batch_utils.write_batch_file(testname,
                                              batch_utils.POSTFIX_UPLOAD1,
                                              args.model,
                                              list_ids_prompts)
batch_utils.upload_file_and_start(batch_filename, args.model)







