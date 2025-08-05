# This is the code to have an LLM generate a strategy freeform
import utils, batch_utils
import sys

assert len(sys.argv) == 3, "usage strategy_num model"
strategy_num = sys.argv[1]
model = sys.argv[2]

filename = utils.get_filename_from_prefix(strategy_num)
authorities_str, background_str, goal_str, strategy_str, analysis_str, \
    adversarial_step_str, primary_area_str, strategy_type_str = utils.parse_file(filename)

goals = utils.strip_numbering(goal_str)
article_goal = "a "
verb_goal = "is"
sing_pl_goal = "goal"
if len(goals) > 1:
    sing_pl_goal = "goals"
    article_goal = ""
    verb_goal = "are"

user_prompt = "You will be coming up with a tax strategy that meets " + article_goal + \
               "specified " + sing_pl_goal + \
               ", given background facts and particular tax-law authorities that the " + \
               "strategy should employ to reach the " + sing_pl_goal + ".\n\n"

user_prompt += "Here are the authorities you will be applying:\n\n" + authorities_str
assert len(background_str.strip()) > 0, "Expected background; generation makes no sense without background facts"
user_prompt += "\n\nHere are the background facts:\n\n" + background_str.strip()
user_prompt += "\n\nHere " + verb_goal + " the " + sing_pl_goal + \
            " the tax strategy should meet:\n\n" + goal_str

testname = batch_utils.get_testname("generate_freeform_" + strategy_num, model)
print("testname=", testname)
batch_filename = batch_utils.write_batch_file(testname,
                                              batch_utils.POSTFIX_UPLOAD1,
                                              model,
                                              [(strategy_num, user_prompt)])
batch_utils.upload_file_and_start(batch_filename, model)

