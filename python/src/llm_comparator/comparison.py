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
"""Entrypoint for running comparative evaluations with LLM Comparator."""

from collections.abc import Sequence
import json
import os
import pathlib
from typing import Optional

from llm_comparator import llm_judge_runner
from llm_comparator import my_types


# TODO(llm-comparator): Provide convenience utilities for converting from, e.g.,
# CSV/TSV to the dictionary format required by this function.
def run(
    inputs: Sequence[my_types.LLMJudgeInput],
    judge: llm_judge_runner.LLMJudgeRunner,
    model_names: Sequence[str] = ('A', 'B'),
    judge_opts: Optional[my_types.JsonDict] = None,
) -> my_types.JsonDict:
  """Runs a comparison with LLM Comparator.

  LLM Comparator comparisons are run in three steps:

  1. An LLM Judge is run on the inputs to produce a set of judgements.
  2. A Rationale Bullet Generator is run on the judgements to produce a set of
     rationale bullets.
  3. The Rationale Cluster Generator is run on the rationale bullets to produce
     a set of rationale clusters with similarity scores.

  Args:
    inputs: The inputs to the evaluation.
    judge: The LLM Judge to use.
    bulletizer: The Rationale Bullet Generator to use.
    clusterer: The Rationale Cluster Generator to use.
    model_names: The names of the models as you would like them to appear in the
      LLM Comparator web application.
    judge_opts: keyword arguments passed to judge.run(). See the
      llm_comparator.llm_judge_runner.LLMJudgeRunner.run() documentation for
      details.
    bulletizer_opts: keyword arguments passed to bulletizer.run(). See the
      llm_comparator.rationale_bullet_generator.RationaleBulletGenerator.run()
      documentation for details.
    clusterer_opts: keyword arguments passed to clusterer.run(). See the
      llm_comparator.rationale_cluster_generator.RationaleClusterGenerator.run()
      documentation for details.

  Returns:
    The evaluation results as a JSON object, or the value of output_path if
    provided and writing to that file was successful.
  """

  judgements = judge.run(inputs, **(judge_opts or {}))

  per_example_generator = zip(inputs, judgements) #, cluster_similarities

  ratings_labels = [jug["rating_labels"] for jug in judgements]

  per_example_rating_labels = zip(inputs, ratings_labels)


  return {
      'metadata': {'custom_fields_schema': [
          {"name": "Case Number", "type": "category"},
          {"name": "Doc Type", "type": "category"},
          {"name": "Model Name", "type": "category"},
          {"name": "Text Reference", "type" : "text"},
          {"name": "Disagreement Reason", "type": "text"},
          {"name" : "Annotator Evaluation", "type" : "text"},
          {"name" : "Annotator Rationale", "type" : "text"}
      ]},
      'models': [{'name': name} for name in model_names],
      'examples': [
          {
              'input_text': input['prompt'],
              'tags': input['tags'],
              'output_text_a': input['response_a'],
              'output_text_b': input['response_b'],
              'score': judgement['score'],
              'individual_rater_scores': judgement['individual_rater_scores'],
              'rationale_list': [], 
              'custom_fields': {
                  "Case Number": input["custom_fields"]["case_number"],
                  "Doc Type" : input["custom_fields"]["doc_type"],
                  "Model Name" : input["custom_fields"]["model_name"],
                  "Text Reference" : input["custom_fields"]["text_reference"],
                  "Disagreement Reason" : input["custom_fields"]["disagreement_reason"],
                  # "Annotator Evaluation" : input["custom_fields"]["a_evaluation"],
                  # "Annotator Rationale" : input["custom_fields"]["a_rationale"],
              },
          }
          for input, judgement in per_example_generator
      ],
      'rationale_clusters': [],
  }, per_example_rating_labels


def write(comparison_result: my_types.JsonDict, file_path: str) -> str:
  with open(file_path, 'w') as f:
    json.dump(comparison_result, f)
  return file_path


def show_in_colab(file_path: str, height: int = 800, port: int = 8888) -> None:
  """Serves the LLM Comparator app from the Colab content directory."""
  import IPython  # pylint: disable=g-import-not-at-top #pytype: disable=import-error

  if (ishell := IPython.get_ipython()) is None:
    raise RuntimeError('Not running in an IPython context.')

  # Copy the website files from the data directory to the Colab content
  # directory if they don't already exist.
  if not os.path.isdir('/content/llm_comparator'):
    website_root = pathlib.Path(__file__).parent / 'data'
    ishell.system_raw(f'cp -R {website_root} /content/llm_comparator')

  # Serve the website from the Colab content directory.
  # TODO(llm-comparator): Check if a server is already running before trying to
  # start a new one.
  ishell.system_raw(f'python3 -m http.server {port} &')

  # Display the served website in an iframe.
  IPython.display.display(IPython.display.Javascript("""
  (async () => {
    const serverAddress = await google.colab.kernel.proxyPort(%s);
    const results_path = serverAddress + '%s';

    const fm = document.createElement('iframe');
    fm.frameBorder = 0
    fm.height = '%d'
    fm.width = '100%%'
    fm.src = serverAddress + 'llm_comparator/?results_path=' + results_path;
    document.body.append(fm)
  })();
  """ % (port, file_path, height)))
