# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Runner for LLM Judge."""

from collections.abc import Sequence
import math
import re
from multiprocessing.connection import answer_challenge
from typing import Optional
from tqdm import tqdm
import os
import json
from collections import defaultdict
from datetime import datetime

from llm_comparator import _logging
from llm_comparator import model_helper_together
from llm_comparator import prompt_templates
from llm_comparator import my_types
from llm_comparator import utils

_IndividualRating = my_types.IndividualRating
_JsonDict = my_types.JsonDict
_LLMJudgeInput = my_types.LLMJudgeInput
_LLMJudgeOutput = my_types.LLMJudgeOutput
_GenerationModelHelper = model_helper_together.GenerationModelHelper

_logger = _logging.logger

DEFAULT_RATING_TO_SCORE_MAP = {
    'Correct': 1.0,
    'Incomplete': 0.5,
    'Inference': 0.5,
    'Wrong': -1,
    'Skipped Question': -0.5,
    'Hallucination': -1.5,
    'Missing Answer': 0,
    'True Negative': 1,
    'Judge Failure': 0
}


class LLMJudgeRunner:
    """Runner for LLM judge that determines which response is better."""

    def __init__(
            self,
            generation_model_helper: _GenerationModelHelper,
            llm_judge_prompt_template=None,
            rating_to_score_map: Optional[dict[str, float]] = None,
    ):
        """Initializes the LLM judge runner.

        Args:
          generation_model_helper: Generative model helper to run the LLM judge.
          llm_judge_prompt_template: Prompt template for LLM judge.
          rating_to_score_map: Map from rating label text to score.
        """
        if llm_judge_prompt_template is None:
            llm_judge_prompt_template = [prompt_templates.COHERENT_JUDGE,
                                         prompt_templates.RECURSIVE_JUDGE]
        self.generation_model_helper = generation_model_helper
        self.llm_judge_prompt_template = llm_judge_prompt_template
        if rating_to_score_map is None:
            rating_to_score_map = DEFAULT_RATING_TO_SCORE_MAP
        self.rating_to_score_map = rating_to_score_map

    def create_prompt_for_recursive_judge(
            self, prompt: str, response_a: str, response_b: str, full_text: str, model_reasoning: str
    ) -> str:
        prompt_for_judge = self.llm_judge_prompt_template[1].format(
            prompt=prompt, response_a=response_a, response_b=response_b, full_text=full_text,
            model_reasoning=model_reasoning
        )

        return prompt_for_judge

    def create_prompt_for_coherence_judge(
            self, prompt: str, response_a: str, text_reference: str
    ) -> str:
        prompt_for_judge = self.llm_judge_prompt_template[0].format(
            prompt=prompt, response_a=response_a, text_reference=text_reference
        )

        return prompt_for_judge

    def create_inputs_with_repeats_for_judge(
            self, inputs: Sequence[_LLMJudgeInput], num_repeats: int
    ) -> Sequence[_JsonDict]:
        """Creates inputs with repeated runs for LLM Judge."""
        inputs_with_repeats = []
        for index, ex in enumerate(inputs):
            # Non-flipped.
            # If num_repeats is an odd number, roundup.
            for _ in range(math.ceil(num_repeats)):
                inputs_with_repeats.append({
                    'example_index': index,
                    'prompt': ex['prompt'],
                    'response_a': ex['response_a'],
                    'response_b': ex['response_b'],
                    "full_text": ex["custom_fields"]["full_text"],
                    "text_reference": ex["custom_fields"]["text_reference"],
                    "model_name": ex["custom_fields"]["model_name"],
                    'is_flipped': False,
                })
        _logger.info('Created %d inputs for LLM judge.', len(inputs_with_repeats))
        return inputs_with_repeats

    def deterministic_outputs(self, input):
        xml_structure = """
    '```xml
    <result>
    <explanation>{explanation}</explanation>
    <verdict>{verdict}</verdict>
    </result>
    ```'
    """

        if input["response_a"] in ["N/A", "N\\A"] and input["response_b"] in ["N/A", "N\\A"]:
            output = xml_structure.format(explanation="A e GTA sono entrambe N/A.", verdict="True Negative")
        if input["response_a"] in ["N/A", "N\\A"] and input["response_b"] not in ["N/A", "N\\A"]:
            output = xml_structure.format(explanation="A è N/A mentre GTA fornisce una risposta.",
                                          verdict="Missing Answer")
        if input["response_a"] == "domanda_saltata":
            output = xml_structure.format(explanation="A è 'domanda saltata', il modello ha saltato la domanda.",
                                          verdict="Skipped Question")

        return output

    def validate_answer(self, out):
        parsed = utils.extract_xml_part(out, "result")
        if not parsed:
            return False
        if (rationale := parsed.find('explanation')) is None:
            return False
        if (rationale := parsed.find('verdict')) is None:
            return False
        return True

    def is_coherent(self, out):
        parsed = utils.extract_xml_part(out, "result")
        if parsed.find('verdict').text == 'Coerente':
            return True
        else:
            return False

    def missing_evaluation(self, explanation, verdict):
        xml_structure = """
      '```xml
      <result>
      <explanation>{explanation}</explanation>
      <verdict>{verdict}</verdict>
      </result>
      ```'
      """
        output = xml_structure.format(explanation=explanation, verdict=verdict)

        return output

    @staticmethod
    def extract_q_number(questions):
        """Extract question number and body from a list of questions and categories."""
        question_parts = defaultdict(dict)
        pattern = re.compile(r'(Q\d+(?:\.\d+)?)\.?\s*(.*)')
        match = pattern.match(questions)
        try:
            question_number = match.group(1)
        except AttributeError:
            question_number = None
            _logger.warning(f"Question number matcher broke")
        return question_number

    def run_query(self, inputs: Sequence[_JsonDict], output_dir, document_type, num_repeats) -> Sequence[str]:
        """Runs LLM judge."""
        judge_inputs = []
        deterministic_judge_outputs = []
        judge_outputs = []
        coherence_outputs = []
        judge_outputs_dict = defaultdict(list)
        judge_repetition = 0
        all_labels = defaultdict(list)

        output_path = os.path.join(output_dir, "judge_runner_results", document_type)
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        for j_input in tqdm(inputs):
            q_n = self.extract_q_number(j_input['prompt'])
            model_name = j_input["model_name"]
            current_labels = list()
            # Filter out Deterministic Cases
            if j_input['response_a'] in ["domanda_saltata", "N/A", "N\\A"]:
                out = self.deterministic_outputs(j_input)
                judge_outputs.append(out)
                judge_outputs_dict[q_n].append(out)
                label = self.parse_xml_output(out)
                current_labels.append(label)
                out_path = os.path.join(output_path, f"{model_name}_judge_runner_{q_n}_deterministic_{judge_repetition}.txt")
                with open(out_path, mode="w", encoding="utf-8") as file:
                    file.write(out)
            else:
                # We need a two step startegy first a coherence judge and then the actual judge.
                judge_input = self.create_prompt_for_coherence_judge(
                    j_input['prompt'], j_input['response_a'], j_input['text_reference'])
                # Validation loop for coherence judge
                i = 0
                out = None  # Initialize out to None
                while i < 5:  # Limit retries to 5
                    out = self.generation_model_helper.predict(judge_input)
                    coherence_outputs.append(out)
                    if self.validate_answer(out):
                        out_path = os.path.join(output_path, f"{model_name}_judge_runner_{q_n}_coherence_{judge_repetition}.txt")
                        # judge_outputs.append(out)
                        judge_outputs_dict[q_n].append(out)
                        label = self.parse_xml_output(out)
                        if not self.is_coherent(out):
                            current_labels.append(f"{label}(Incoherent)")
                        with open(out_path, mode="w", encoding="utf-8") as file:
                            file.write(out)
                        break  # Exit the loop immediately if validation succeeds
                    _logger.warning(f"Repeating the generation for coherence judge for the {i + 1}-th time")
                    i += 1  # Increment i only if validation fails
                if i == 5:
                    _logger.warning("Exceeded maximum retry attempts for coherence judge. Assuming coherence")
                    out = self.missing_evaluation(explanation="Troppi tentativi, viene assunta coerenza",
                                                  verdict="Coerente")
                # # Check the output, is there coherence or not?
                # if not self.is_coherent(out):
                #     judge_outputs.append(out)
                #     judge_outputs_dict[q_n].append(out)
                #     label = self.parse_xml_output(out)
                #     current_labels.append(label)
                #     # continue
                judge_input = self.create_prompt_for_recursive_judge(
                    prompt=j_input['prompt'], response_a=j_input['response_a'], response_b=j_input['response_b'],
                    full_text=j_input['full_text'], model_reasoning=j_input['text_reference'])
                # Validate loop for recursive judge
                i = 0
                out = None  # Initialize out to None
                while i < 5:  # Limit retries to 5
                    out = self.generation_model_helper.predict(judge_input)
                    if self.validate_answer(out):
                        out_path = os.path.join(output_path, f"{model_name}_judge_runner_{q_n}_recurrent_{judge_repetition}.txt")
                        judge_outputs.append(out)
                        judge_outputs_dict[q_n].append(out)
                        label = self.parse_xml_output(out)
                        current_labels.append(label)
                        with open(out_path, mode="w", encoding="utf-8") as file:
                            file.write(out)
                        break  # Exit the loop immediately if validation succeeds
                    _logger.warning(f"Repeating the generation for recursive judge for the {i + 1}-th time")
                    i += 1  # Increment i only if validation fails

                if i == 5:  # Check if all retries were exhausted
                    _logger.warning("Exceeded maximum retry  for recursive judge. Using missing evaluation.")
                    out = self.missing_evaluation(explanation="Il giudice LLM non ha valutato questo caso",
                                                  verdict="Judge Failure")
                    out_path = os.path.join(output_path, f"{model_name}_judge_runner_{q_n}_recurrent_{judge_repetition}.txt")
                    with open(out_path, mode="w", encoding="utf-8") as file:
                        file.write(out)

                    judge_outputs.append(out)
                    judge_outputs_dict[q_n].append(out)
                    label = self.parse_xml_output(out)
                    current_labels.append(label)

            all_labels[judge_repetition].append({model_name: {q_n: current_labels}})
            judge_repetition += 1
            if judge_repetition == num_repeats:
                judge_repetition = 0

            out_path = os.path.join(output_path, f"judge_runner_all_labels.json")
            with open(out_path, mode="w") as file:
                json.dump(all_labels, file, indent=4)
        _logger.info('Generated %d outputs from LLM judge.', len(judge_outputs))
        return judge_outputs

    def parse_xml_output(self, raw_output: str):
        # Find parts where <result> is in the XML-formatted output.
        parsed_xml = utils.extract_xml_part(raw_output, 'result')
        if not parsed_xml:
            return 'Parsing Error'
        if (rating_label := parsed_xml.find('verdict')) is None:
            return 'Parsing Error'
        if (rating_label := rating_label.text) is None:
            return 'Parsing Error'
        _logger.info(f"This is the rating_label: {rating_label}")
        return rating_label

    # TODO(b/344919097): Add some unit tests.
    def parse_results(
            self,
            outputs_from_judge: Sequence[str],
            inputs_for_judge: Sequence[_JsonDict],
    ) -> Sequence[Sequence[_IndividualRating]]:
        """Parses XML-formatted LLM judge outputs."""

        def parse_output(raw_output: str):
            # Find parts where <result> is in the XML-formatted output.
            parsed_xml = utils.extract_xml_part(raw_output, 'result')
            if not parsed_xml:
                return None

            if (rationale := parsed_xml.find('explanation')) is None:
                return None
            if (rationale := rationale.text) is None:
                return None

            if (rating_label := parsed_xml.find('verdict')) is None:
                return None
            if (rating_label := rating_label.text) is None:
                return None
            _logger.info(f"This is the rating_label: {rating_label}")
            try:
                score = 0
                for rate in rating_label.split(","):
                    score += self.rating_to_score_map.get(rate.strip(), 1)
            except KeyError:
                _logger.error(
                    'LLM judge returned an unknown rating label: %s}', rating_label
                )
                return None
            _logger.info(f"This is the score: {score}, rating_label: {rating_label}, rationale: {rationale}")
            return (score, rating_label, rationale.strip(' \n'))

        max_example_index = max([ex['example_index'] for ex in inputs_for_judge])
        example_ratings = [[] for _ in range(max_example_index + 1)]

        for judge_input, raw_output in zip(inputs_for_judge, outputs_from_judge):
            parsed_output = parse_output(raw_output)
            if parsed_output:
                example_ratings[judge_input['example_index']].append({
                    'is_flipped': judge_input['is_flipped'],
                    'score': (
                        parsed_output[0] * -1.0 if judge_input['is_flipped'] else parsed_output[0]
                    ),
                    'rating_label': parsed_output[1],
                    'rationale': parsed_output[2],
                })
        _logger.info('Parsed %d example ratings.', len(example_ratings))
        return example_ratings

    def postprocess_results(
            self, example_ratings: Sequence[Sequence[_IndividualRating]]
    ) -> Sequence[_LLMJudgeOutput]:
        results: list[_LLMJudgeOutput] = []
        for ratings in example_ratings:
            score = sum([rating['score'] for rating in ratings]) / len(ratings)
            results.append({
                'score': score,
                'individual_rater_scores': list(ratings),
                'rating_labels': [rating['rating_label'] for rating in ratings]
            })
        return results

    def run(
            self, inputs: Sequence[_LLMJudgeInput], output_dir="/output", num_repeats=6, document_type=''
    ) -> Sequence[_LLMJudgeOutput]:
        """Runs the LLM judge pipeline."""

        input_list_for_judge = self.create_inputs_with_repeats_for_judge(
            inputs, num_repeats
        )
        outputs_from_judge = self.run_query(input_list_for_judge, output_dir, document_type, num_repeats)
        example_ratings = self.parse_results(
            outputs_from_judge, input_list_for_judge
        )
        scores_and_ratings = self.postprocess_results(example_ratings)
        _logger.info('Generated ratings for %d examples.', len(scores_and_ratings))
        return scores_and_ratings
