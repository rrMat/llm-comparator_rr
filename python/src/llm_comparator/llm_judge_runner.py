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

from llm_comparator import _logging
from llm_comparator import model_helper
from llm_comparator import prompt_templates
from llm_comparator import my_types
from llm_comparator import utils


_IndividualRating = my_types.IndividualRating
_JsonDict = my_types.JsonDict
_LLMJudgeInput = my_types.LLMJudgeInput
_LLMJudgeOutput = my_types.LLMJudgeOutput
_GenerationModelHelper = model_helper.GenerationModelHelper

_logger = _logging.logger


DEFAULT_RATING_TO_SCORE_MAP = {
    'Correct': 1.0,
    'Incomplete': 0.5,
    'Inference' : 0.5,
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
      self, prompt: str, response_a: str, response_b: str, full_text: str
  ) -> str:
    prompt_for_judge = self.llm_judge_prompt_template[1].format(
        prompt=prompt, response_a=response_a, response_b=response_b, full_text=full_text
    )

    return prompt_for_judge

  def create_prompt_for_coherence_judge(
      self, prompt: str, response_a: str, text_reference: str
  ) -> str:
    prompt_for_judge = self.llm_judge_prompt_template[0].format(
        prompt=prompt, response_a=response_a,  text_reference=text_reference
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
            "full_text" : ex["custom_fields"]["full_text"],
            "text_reference" : ex["custom_fields"]["text_reference"],
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

    if input["response_a"] == "N/A" and input["response_b"] == "N/A":
        output = xml_structure.format(explanation= "A e GTA sono entrambe N/A.",verdict = "True Negative")
    if input["response_a"] == "N/A" and input["response_b"] != "N/A":
        output = xml_structure.format(explanation="A è N/A mentre GTA fornisce una risposta.", verdict="Missing Answer")
    if input["response_a"] == "domanda_saltata":
        output = xml_structure.format(explanation="A è 'domanda saltata', il modello ha saltato la domanda.", verdict="Skipped Question")

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
      output = xml_structure.format(explanation= explanation, verdict = verdict)

      return output


  def run_query(self, inputs: Sequence[_JsonDict]) -> Sequence[str]:
    """Runs LLM judge."""
    judge_inputs = []
    deterministic_judge_outputs = []
    judge_outputs = []
    for j_input in tqdm(inputs):
        # Filter out Deterministic Cases
        if j_input['response_a'] in ["domanda_saltata", "N/A"]:
            judge_outputs.append(self.deterministic_outputs(j_input))
        else:
            # We need a two step startegy first a coherence judge and then the actual judge.
            judge_input = self.create_prompt_for_coherence_judge(
                j_input['prompt'], j_input['response_a'],j_input['text_reference'])
            #Validation loop for coherence judge
            i = 0
            out = None  # Initialize out to None
            while i < 5:  # Limit retries to 5
                out = self.generation_model_helper.predict(judge_input)
                if self.validate_answer(out):
                    break  # Exit the loop immediately if validation succeeds
                _logger.warning(f"Repeating the generation for coherence judge for the {i + 1}-th time")
                i += 1  # Increment i only if validation fails
            if i == 5:
                _logger.warning("Exceeded maximum retry attempts for coherence judge. Assuming coherence")
                out = self.missing_evaluation(explanation="Troppi tentativi, viene assunta coerenza", verdict="Coerente" )
            # Check the output, is there coherence or not?
            if not self.is_coherent(out):
                judge_outputs.append(out)
                continue
            else:
                judge_input = self.create_prompt_for_recursive_judge(
                    j_input['prompt'], j_input['response_a'], j_input['response_b'], j_input['full_text'])
                # Validate loop for recursive judge
                i = 0
                out = None  # Initialize out to None
                while i < 5:  # Limit retries to 5
                    out = self.generation_model_helper.predict(judge_input)
                    if self.validate_answer(out):
                        break  # Exit the loop immediately if validation succeeds
                    _logger.warning(f"Repeating the generation for recursive judge for the {i + 1}-th time")
                    i += 1  # Increment i only if validation fails

                if i == 5:  # Check if all retries were exhausted
                    _logger.warning("Exceeded maximum retry  for recursive judge. Using missing evaluation.")
                    out = self.missing_evaluation(explanation="Il giudice LLM non ha valutato questo caso", verdict="Judge Failure")

                judge_outputs.append(out)

    _logger.info('Generated %d outputs from LLM judge.', len(judge_outputs))
    return judge_outputs

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
        score = self.rating_to_score_map[rating_label]
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
          'rating_labels' : [rating['rating_label'] for rating in ratings]
      })
    return results

  def run(
      self, inputs: Sequence[_LLMJudgeInput], num_repeats=6
  ) -> Sequence[_LLMJudgeOutput]:
    """Runs the LLM judge pipeline."""
    self.num_repeats = num_repeats
    input_list_for_judge = self.create_inputs_with_repeats_for_judge(
        inputs, num_repeats
    )
    outputs_from_judge = self.run_query(input_list_for_judge)
    example_ratings = self.parse_results(
        outputs_from_judge, input_list_for_judge
    )
    scores_and_ratings = self.postprocess_results(example_ratings)
    _logger.info('Generated ratings for %d examples.', len(scores_and_ratings))
    return scores_and_ratings
