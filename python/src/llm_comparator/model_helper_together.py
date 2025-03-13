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
"""Classes for calling generating LLMs and embedding models."""

import abc
from collections.abc import Iterable, Sequence
import time
from typing import Optional
from tqdm import tqdm

from llm_comparator import _logging

from together import Together
import torch


_logger = _logging.logger


class GenerationModelHelper(abc.ABC):
  """Class for managing calling LLMs."""

  def predict(self, prompt: str) -> str:
    raise NotImplementedError()

  def predict_batch(self, prompts: Sequence[str]) -> Sequence[str]:
    raise NotImplementedError()


class EmbeddingModelHelper(abc.ABC):
  """Class for managing calling text embedding models."""

  def embed(self, text: str) -> Sequence[float]:
    raise NotImplementedError()

  def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
    raise NotImplementedError()



class TogetherGeneration(GenerationModelHelper):
    """TogetherAi text generation"""

    def __init__(self, temperature, max_new_tokens, top_p, top_k, repetition_penalty, model_name: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"):
        self.llm = Together()
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty


    def predict(self, prompt: str) -> str:
        if not prompt:
            print("No messages provided.")
            return ""

        messages = {"role": "system", "content": prompt},

        try:
            generated_ids = self.llm.chat.completions.create(
                model = self.model_name,
                messages = messages,
                temperature = self.temperature,
                max_tokens = self.max_new_tokens,
                top_p = self.top_p,
                top_k = self.top_k,
                repetition_penalty = self.repetition_penalty
            )

            response = generated_ids.choices[0].message.content
            return response

        except Exception as e:
            print(f"Error during TogetherAI chat generation: {e}")
            return ""

    def predict_batch(self, batch_of_messages: Sequence[str]) -> Sequence[str]:
        """
        Runs predict_chat on a batch of conversations.
        Each item in 'batch_of_messages' is a list of dicts representing a conversation.
        """
        results = []
        for prompt in tqdm(batch_of_messages):
            output = self.predict(
                prompt
            )
            results.append(output)
            tqdm.write(f"results: {results}")
        return results
