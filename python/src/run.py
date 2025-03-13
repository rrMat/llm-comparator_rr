from llm_comparator import comparison
from llm_comparator import model_helper_together
from llm_comparator import llm_judge_runner
from llm_comparator.model_helper_together import TogetherGeneration

import pickle

import os


def llm_judge_evaluation(llm_judge_inputs):


    comparison_results = None

    generator =  TogetherGeneration(temperature=0, max_new_tokens=2048, model_name="Qwen/Qwen2.5-7B-Instruct-Turbo")
    judge = llm_judge_runner.LLMJudgeRunner(generator)
    comparison_result, llm_evaluations_zip = comparison.run(
        llm_judge_inputs,
        judge,
        model_names=["LLM Response", "Ground Truth"],
        judge_opts={"num_repeats": 1}
    )
    print("stop")

    # for each_case_number, case_content in llm_judge_inputs.items():
    #     for each_document_type, document_content in case_content.items():
    #         comparison_result = comparison.run(
    #             document_content,
    #             judge,
    #             model_names=["LLM Response", "Ground Truth"],
    #             judge_opts={"num_repeats": 3}
    #         )



            # case_number_document_type_file_path = os.path.join(self.config["results_dir"],
            #                                                    self.config["judge_evaluation_object"].split(sep)[0],
            #                                                    f"{each_case_number}_{each_document_type}_llm_comparator_judge_evaluation.json")
            # comparison.write(comparison_result, case_number_document_type_file_path)
            #
            # if comparison_results is None:
            #     comparison_results = comparison_result
            # else:
            #     if comparison_result.get("metadata") != comparison_results.get("metadata"):
            #         logger.warning(f"[{self.__class__.__name__}] Warning: metadata in "
            #                        f"{each_case_number}-{each_document_type} does not match. LLM Judge Evaluation "
            #                        f"responses are ({comparison_result.get('metadata')}, {comparison_results.get('metadata')})")
            #     if comparison_result.get("models") != comparison_results.get("models"):
            #         logger.warning(f"[{self.__class__.__name__}] Warning: models in "
            #                        f"{each_case_number}-{each_document_type} does not match. LLM Judge Evaluation "
            #                        f"responses are ({comparison_result.get('models')}, {comparison_results.get('models')})")
            #     if comparison_result.get("rationale_clusters") != comparison_results.get("rationale_clusters"):
            #         logger.warning(f"[{self.__class__.__name__}] Warning: rationale_clusters in "
            #                        f"{each_case_number}-{each_document_type} does not match. LLM Judge Evaluation "
            #                        f"responses are ({comparison_result.get('rationale_clusters')}, {comparison_results.get('rationale_clusters')})")
            #
            #     examples = comparison_result.get("examples", {})
            #     comparison_results["examples"].extend(examples)
    return comparison_results

path = r"C:\Users\matte\PycharmProjects\equal\output\results\judge_11-03-2025-17-03-11_Mistral_Qwen\llm_judge_comparator_preprocessing.pkl"
with open(path, 'rb') as file:
    data = pickle.load(file)
francesca = data["Caso_127"]["tribunale"][0:87]
# francesca.extend(data["Caso_127"]["tribunale"][212:299])
result = llm_judge_evaluation(llm_judge_inputs =francesca)