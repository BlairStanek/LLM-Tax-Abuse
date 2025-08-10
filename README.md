# Can LLMs Identify Tax Abuse?
This is the code and data corresponding to the paper *Can LLMs Identify Tax Abuse?*.  Our research produced what we believe to be the first LLM-generated novel tax strategy.  The relevant LLM input and output are in `Novel_Tax_Strategy_17.pdf`, which also contains a brief analysis of why the strategy is novel and fundamentally different from the most similar known tax strategy. 

As described in the paper, the research involved 36 domain-expert-created files providing details of past U.S. tax-minimization strategies.  Five of these 36 strategies are here in the directory `Strategies`, and our python code runs against these five.  The remainder are not being published to ensure they are not used to train the next version of LLMs, which would severely diminish their utility for assessing LLM abilities in this area.  

All calls are via batch API, meaning every task involves running at least two python files to work (to call the API and then to fetch from the API).  You will have to note the relevant API's batch identifier and this code's test name, to pass them to the next step.  Each API's web console has a way to monitor the progress of each batch, e.g. https://platform.openai.com/batches/.  

For the analysis verification task, you kick off with `analysis_verification.py`, then call `binary_answers_clarify.py`, then `binary_answers_finalize.py`.  

For the goal verification task (with or without analysis) and the adversarial step goal-failure verification, you kick off with `goal_verification.py`, then call `binary_answers_clarify.py`, then `binary_answers_finalize.py`.  

For the step-close task, you kick off with `step_cloze_start.py`, then call `step_cloze_grade.py`, then `step_cloze_finalize.py`.  

For from-scratch strategy generation, you kick off with `generate_freeform.py`, then call `generate_freeform_retrieve.py`.  

For grading from-scratch strategy generation, you kick off with `freeform_grade.py`, then call `freeform_grade_finalize.py`.  
