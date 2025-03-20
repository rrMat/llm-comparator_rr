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
from typing import Optional, List, Any
from tqdm import tqdm

from llm_comparator import _logging

from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
from sentence_transformers import SentenceTransformer
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


class HuggingFaceGenerationModelHelper(GenerationModelHelper):
    """HuggingFace text generation model helper."""

    def __init__(self, temperature, max_new_tokens, top_p, top_k, repetition_penalty,
                 model_name: str = 'Qwen/Qwen2.5-7B-Instruct', use_8bit: bool = False, use_4bit: bool = False):

        self.device = torch.device("mps" if torch.backends.mps.is_available()
                                   else "cuda" if torch.cuda.is_available() else "cpu")
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty

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
        elif use_4bit and use_8bit:
            raise AttributeError(
                f"It is not logically correct to initialize 4bit and 8bit quantization options together. "
                f"Please select one or neither of them!")
        else:
            if self.device.type == 'mps':
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                ).to(self.device)
            else:
                self.generator = pipeline('text-generation', model=model_name)
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)

    def predict(self, prompt: str) -> str:

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
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                num_return_sequences=self.repetition_penalty
            )

            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]

            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            # Strip the prompt tokens
            print(f"response: {response}")
            return response
        except Exception as e:
            _logger.error(f"Error during LLM chat generation: {e}")
            return ""

    def predict_batch(self, batch_of_messages: Sequence[str]) -> Sequence[str]:
        """
        Runs predict_chat on a batch of conversations.
        Each item in 'batch_of_messages' is a list of dicts representing a conversation.
        """
        results = []
        for prompt in tqdm(batch_of_messages):
            output = self.predict(
                prompt,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                repetition_penalty=self.repetition_penalty
            )
            results.append(output)
            tqdm.write(f"results: {results}")
        return results


class HuggingFaceEmbeddingModelHelper(EmbeddingModelHelper):
    """HuggingFace embedding model helper."""

    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2', use_8bit: bool = False,
                 use_4bit: bool = False):
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


class HuggingFaceVLLMGenerationModelHelper(GenerationModelHelper):
    """HuggingFace text generation model helper."""

    def __init__(self, temperature, max_new_tokens, top_p, top_k, repetition_penalty,
                 model_name: str = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"):

        from vllm import LLM, SamplingParams

        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty

        self.sampling_params = SamplingParams(max_tokens=self.max_new_tokens,
                                              temperature=self.temperature,
                                              top_p=self.top_p,
                                              top_k=self.top_k,
                                              repetition_penalty=self.repetition_penalty)
        self.model = LLM(model=model_name, quantization="AWQ")

    def predict(self, prompt: str) -> (str | List[Any]):

        if not prompt:
            print("No messages provided.")
            return ""

        try:
            generated_ids = self.model.generate(prompt, self.sampling_params)

            response = [
                generated_id.outputs[0].text for generated_id in generated_ids
            ]

            print(f"response: {response}")
            return response
        except Exception as e:
            _logger.error(f"Error during LLM chat generation: {e}")
            return ""

    def predict_batch(self, batch_of_messages: Sequence[str]) -> (str | list[list[Any]]):
        """
        Runs predict_chat on a batch of conversations.
        Each item in 'batch_of_messages' is a list of dicts representing a conversation.
        """
        results = []
        for prompt in tqdm(batch_of_messages):
            try:
                generated_ids = self.model.generate(prompt, self.sampling_params)

                response = [
                    generated_id.outputs[0].text for generated_id in generated_ids
                ]

                # Strip the prompt tokens
                print(f"response: {response}")
                results.append(response)
            except Exception as e:
                _logger.error(f"Error during LLM chat generation: {e}")
                return ""
        return results


class HuggingFaceLlamaCPPGenerationModelHelper(GenerationModelHelper):
    """HuggingFace text generation model helper."""

    def __init__(self, temperature, max_new_tokens, top_p, top_k, repetition_penalty,
                 model_name, model_filename, input_context_length, cache_dir):

        from llama_cpp import Llama

        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.repetition_penalty = repetition_penalty

        self.model = Llama.from_pretrained(repo_id=model_name,
                                           filename=model_filename,
                                           cache_dir=cache_dir,
                                           n_ctx=input_context_length,
                                           verbose=True)

    def predict(self, prompt: str) -> (str | List[Any]):

        if not prompt:
            print("No messages provided.")
            return ""

        try:
            messages = {"role": "system", "content": prompt},

            generated_ids = self.model.create_chat_completion(
                messages=messages,
                max_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                repeat_penalty=self.repetition_penalty
            )
            response = generated_ids["choices"][0]["message"]["content"]

            print(f"response: {response}")
            return response
        except Exception as e:
            _logger.error(f"Error during LLM chat generation: {e}")
            return ""

    def predict_batch(self, batch_of_messages: Sequence[str]) -> Sequence[str]:
        """
        Runs predict_chat on a batch of conversations.
        Each item in 'batch_of_messages' is a list of dicts representing a conversation.
        """
        results = []
        for prompt in tqdm(batch_of_messages):
            messages = {"role": "system", "content": prompt},
            # Format the chat messages into a single string
            generated_ids = self.model.create_chat_completion(
                messages=messages,
                max_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                repeat_penalty=self.repetition_penalty
            )
            response = generated_ids["choices"][0]["message"]["content"]
            results.append(response)
            tqdm.write(f"results: {results}")
        return results
