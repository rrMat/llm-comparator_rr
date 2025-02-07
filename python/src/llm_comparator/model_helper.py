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

from vertexai import generative_models
from vertexai import language_models


from llm_comparator import _logging

from sentence_transformers import SentenceTransformer

from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
import bitsandbytes as bnb
import torch

MAX_NUM_RETRIES = 5
DEFAULT_MAX_OUTPUT_TOKENS = 256

BATCH_EMBED_SIZE = 100

_logger = _logging.logger


class GenerationModelHelper(abc.ABC):
  """Class for managing calling LLMs."""

  def predict(self, prompt: str, **kwargs) -> str:
    raise NotImplementedError()

  def predict_batch(self, prompts: Sequence[str], **kwargs) -> Sequence[str]:
    raise NotImplementedError()


class EmbeddingModelHelper(abc.ABC):
  """Class for managing calling text embedding models."""

  def embed(self, text: str) -> Sequence[float]:
    raise NotImplementedError()

  def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
    raise NotImplementedError()


class HuggingFaceGenerationModelHelper(GenerationModelHelper):
    """HuggingFace text generation model helper."""

    def __init__(self, model_name: str = 'EleutherAI/gpt-neo-2.7B', use_8bit: bool = False, use_4bit: bool = False):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if use_4bit or use_8bit:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=use_4bit,
                load_in_8bit=use_8bit,
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map='auto'
            ).to(self.device)
        else:
            self.generator = pipeline('text-generation', model=model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def predict(
        self,
        prompt: str,
        max_new_tokens: int = 200,
        temperature: float = 0.3,
        top_p = 0.7,
        top_k = 15,
    ) -> str:

        if not prompt:
            print("No messages provided.")
            return ""
        
        messages = {"role": "system", "content": prompt},
        # Format the chat messages into a single string
        formatted_chat = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        model_inputs = self.tokenizer([formatted_chat], return_tensors="pt").to(self.model.device)

        try:
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                num_return_sequences=1
            )
            
            generated_ids = [
                    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]

            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            # Strip the prompt tokens
            print(f"response: {response}")
            return response
        except Exception as e:
            _logger.error(f"Error during Qwen chat generation: {e}")
            return ""

    def predict_batch(
        self,
        batch_of_messages: Sequence[str],
        max_new_tokens: int = 200,
        temperature: float = 0.3,
        top_p = 0.7,
        top_k = 15,
    ) -> Sequence[str]:
        """
        Runs predict_chat on a batch of conversations.
        Each item in 'batch_of_messages' is a list of dicts representing a conversation.
        """
        results = []
        for prompt in tqdm(batch_of_messages):
            output = self.predict(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
            )
            results.append(output)
            tqdm.write(f"results: {results}")
        return results


class HuggingFaceEmbeddingModelHelper(EmbeddingModelHelper):
    """HuggingFace embedding model helper."""

    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2', use_8bit: bool = False, use_4bit: bool = False):
        if use_4bit:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name, load_in_4bit=True, device_map='auto')
        elif use_8bit:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name, load_in_8bit=True, device_map='auto')
        else:
            self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> Sequence[float]:
        if not text:
            return []
        try:
            if hasattr(self, 'tokenizer'):
                inputs = self.tokenizer(text, return_tensors='pt').to(self.model.device)
                outputs = self.model(**inputs)
                embedding = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
            else:
                embedding = self.model.encode(text)
            print(f"embedding: {embedding}")
            return embedding
        except Exception as e:
            _logger.error(f'Error during HuggingFace embedding: {e}')
            return []

    def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        if not texts:
            return []
        try:
            if hasattr(self, 'tokenizer'):
                inputs = self.tokenizer(texts, return_tensors='pt', padding=True, truncation=True).to(self.model.device)
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1).tolist()
            else:
                embeddings = self.model.encode(texts)
            print(f"embeddings: {embeddings}")
            return embeddings
        except Exception as e:
            _logger.error(f'Error during HuggingFace embedding batch: {e}')
            return []




class VertexGenerationModelHelper(GenerationModelHelper):
  """Vertex AI text generation model API calls."""

  def __init__(self, model_name='gemini-pro'):
    self.engine = generative_models.GenerativeModel(model_name)

  def predict(
      self,
      prompt: str,
      temperature: Optional[float] = None,
      max_output_tokens: Optional[int] = DEFAULT_MAX_OUTPUT_TOKENS,
  ) -> str:
    if not prompt:
      return ''
    num_attempts = 0
    response = None
    prediction = None

    while num_attempts < MAX_NUM_RETRIES and response is None:
      num_attempts += 1

      try:
        prediction = self.engine.generate_content(
            prompt,
            generation_config=generative_models.GenerationConfig(
                temperature=temperature,
                candidate_count=1,
                max_output_tokens=max_output_tokens,
            ),
        )
      except Exception as e:  # pylint: disable=broad-except
        if 'quota' in str(e):
          _logger.info('\033[31mQuota limit exceeded.\033[0m')
        wait_time = 2**num_attempts
        _logger.info('\033[31mWaiting %ds to retry...\033[0m', wait_time)
        time.sleep(2**num_attempts)

    if isinstance(prediction, Iterable):
      prediction = list(prediction)[0]

    return prediction.text if prediction is not None else ''

  def predict_batch(
      self,
      prompts: Sequence[str],
      temperature: Optional[float] = None,
      max_output_tokens: Optional[int] = DEFAULT_MAX_OUTPUT_TOKENS,
  ) -> Sequence[str]:
    outputs = []
    for i in tqdm.auto.tqdm(range(0, len(prompts))):
      # TODO(b/344631023): Implement multiprocessing.
      outputs.append(self.predict(prompts[i], temperature, max_output_tokens))
    return outputs


class EmbeddingModelHelper(abc.ABC):
  """Class for managing calling text embedding models."""

  def embed(self, text: str) -> Sequence[float]:
    raise NotImplementedError()

  def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
    raise NotImplementedError()


class VertexEmbeddingModelHelper(EmbeddingModelHelper):
  """Vertex AI text embedding model API calls."""

  def __init__(self, model_name: str = 'textembedding-gecko@003'):
    self.model = language_models.TextEmbeddingModel.from_pretrained(model_name)

  def _embed_single_run(
      self, texts: Sequence[str]
  ) -> Sequence[Sequence[float]]:
    """Embeds a list of strings into the models embedding space."""
    num_attempts = 0
    embeddings = None

    if not isinstance(texts, list):
      texts = list(texts)

    while num_attempts < MAX_NUM_RETRIES and embeddings is None:
      try:
        embeddings = self.model.get_embeddings(texts)
      except Exception as e:  # pylint: disable=broad-except
        wait_time = 2**num_attempts
        _logger.info('Waiting %ds to retry... (%s)', wait_time, e)
        time.sleep(wait_time)

    if embeddings is None:
      return []

    return [embedding.values for embedding in embeddings]

  def embed(self, text: str) -> Sequence[float]:
    results = self._embed_single_run([text])
    return results[0]

  def embed_batch(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
    if len(texts) <= BATCH_EMBED_SIZE:
      return self._embed_single_run(texts)
    else:
      results = []
      for batch_start_index in tqdm.auto.tqdm(
          range(0, len(texts), BATCH_EMBED_SIZE)
      ):
        results.extend(
            self._embed_single_run(
                texts[batch_start_index : batch_start_index + BATCH_EMBED_SIZE]
            )
        )
      return results
