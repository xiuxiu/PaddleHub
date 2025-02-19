# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"
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
from typing import Dict, List, Optional, Union, Tuple
import csv
import io
import os

import numpy as np
import paddle

from paddlehub.env import DATA_HOME
from paddlehub.text.bert_tokenizer import BertTokenizer
from paddlehub.text.tokenizer import CustomTokenizer
from paddlehub.utils.log import logger
from paddlehub.utils.utils import download
from paddlehub.utils.xarfile import is_xarfile, unarchive


class InputExample(object):
    """
    The input data structure of Transformer modules (BERT, ERNIE and so on).
    """

    def __init__(self, guid: int, text_a: str, text_b: Optional[str] = None, label: Optional[str] = None):
        """
        The input data structure.
        Args:
          guid (:obj:`int`):
              Unique id for the input data.
          text_a (:obj:`str`, `optional`, defaults to :obj:`None`):
              The first sequence. For single sequence tasks, only this sequence must be specified.
          text_b (:obj:`str`, `optional`, defaults to :obj:`None`):
              The second sequence if sentence-pair.
          label (:obj:`str`, `optional`, defaults to :obj:`None`):
              The label of the example.
        Examples:
            .. code-block:: python
                from paddlehub.datasets.base_nlp_dataset import InputExample
                example = InputExample(guid=0,
                                text_a='15.4寸笔记本的键盘确实爽，基本跟台式机差不多了',
                                text_b='蛮喜欢数字小键盘，输数字特方便，样子也很美观，做工也相当不错',
                                label='1')
        """
        self.guid = guid
        self.text_a = text_a
        self.text_b = text_b
        self.label = label

    def __str__(self):
        if self.text_b is None:
            return "text={}\tlabel={}".format(self.text_a, self.label)
        else:
            return "text_a={}\ttext_b={},label={}".format(self.text_a, self.text_b, self.label)


class BaseNLPDataset(object):
    """
    The virtual base class for nlp datasets, such TextClassificationDataset, SeqLabelingDataset, and so on.
    The base class must be supered and re-implemented the method _read_file.
    """

    def __init__(self,
                 base_path: str,
                 tokenizer: Union[BertTokenizer, CustomTokenizer],
                 max_seq_len: Optional[int] = 128,
                 mode: Optional[str] = "train",
                 data_file: Optional[str] = None,
                 label_file: Optional[str] = None,
                 label_list: Optional[List[str]] = None):
        """
        Ags:
            base_path (:obj:`str`): The directory to the whole dataset.
            tokenizer (:obj:`BertTokenizer` or :obj:`CustomTokenizer`):
                It tokenizes the text and encodes the data as model needed.
            max_seq_len (:obj:`int`, `optional`, defaults to :128):
                If set to a number, will limit the total sequence returned so that it has a maximum length.
            mode (:obj:`str`, `optional`, defaults to `train`):
                It identifies the dataset mode (train, test or dev).
            data_file(:obj:`str`, `optional`, defaults to :obj:`None`):
                The data file name, which is relative to the base_path.
            label_file(:obj:`str`, `optional`, defaults to :obj:`None`):
                The label file name, which is relative to the base_path.
                It is all labels of the dataset, one line one label.
            label_list(:obj:`List[str]`, `optional`, defaults to :obj:`None`):
                The list of all labels of the dataset
        """
        self.data_file = os.path.join(base_path, data_file)
        self.label_list = label_list

        self.mode = mode
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len

        if label_file:
            self.label_file = os.path.join(base_path, label_file)
            if not self.label_list:
                self.label_list = self._load_label_data()
            else:
                logger.warning("As label_list has been assigned, label_file is noneffective")
        if self.label_list:
            self.label_map = {item: index for index, item in enumerate(self.label_list)}

    def _load_label_data(self):
        """
        Loads labels from label file.
        """
        if os.path.exists(self.label_file):
            with open(self.label_file, "r", encoding="utf8") as f:
                return f.read().strip().split("\n")
        else:
            raise RuntimeError("The file {} is not found.".format(self.label_file))

    def _download_and_uncompress_dataset(self, destination: str, url: str):
        """
        Downloads dataset and uncompresses it.
        Args:
           destination (:obj:`str`): The dataset cached directory.
           url (:obj: str): The link to be downloaded a dataset.
        """
        if not os.path.exists(destination):
            dataset_package = download(url=url, path=DATA_HOME)
            if is_xarfile(dataset_package):
                unarchive(dataset_package, DATA_HOME)
        else:
            logger.info("Dataset {} already cached.".format(destination))

    def _read_file(self, input_file: str, is_file_with_header: bool = False):
        """
        Reads the files.
        Args:
            input_file (:obj:str) : The file to be read.
            is_file_with_header(:obj:bool, `optional`, default to :obj: False) :
                Whether or not the file is with the header introduction.
        """
        raise NotImplementedError

    def get_labels(self):
        """
        Gets all labels.
        """
        return self.label_list


class TextClassificationDataset(BaseNLPDataset, paddle.io.Dataset):
    """
    The dataset class which is fit for all datatset of text classification.
    """

    def __init__(self,
                 base_path: str,
                 tokenizer: Union[BertTokenizer, CustomTokenizer],
                 max_seq_len: int = 128,
                 mode: str = "train",
                 data_file: str = None,
                 label_file: str = None,
                 label_list: list = None,
                 is_file_with_header: bool = False):
        """
        Ags:
            base_path (:obj:`str`): The directory to the whole dataset.
            tokenizer (:obj:`BertTokenizer` or :obj:`CustomTokenizer`):
                It tokenizes the text and encodes the data as model needed.
            max_seq_len (:obj:`int`, `optional`, defaults to :128):
                If set to a number, will limit the total sequence returned so that it has a maximum length.
            mode (:obj:`str`, `optional`, defaults to `train`):
                It identifies the dataset mode (train, test or dev).
            data_file(:obj:`str`, `optional`, defaults to :obj:`None`):
                The data file name, which is relative to the base_path.
            label_file(:obj:`str`, `optional`, defaults to :obj:`None`):
                The label file name, which is relative to the base_path.
                It is all labels of the dataset, one line one label.
            label_list(:obj:`List[str]`, `optional`, defaults to :obj:`None`):
                The list of all labels of the dataset
            is_file_with_header(:obj:bool, `optional`, default to :obj: False) :
                Whether or not the file is with the header introduction.
        """
        super(TextClassificationDataset, self).__init__(
            base_path=base_path,
            tokenizer=tokenizer,
            max_seq_len=max_seq_len,
            mode=mode,
            data_file=data_file,
            label_file=label_file,
            label_list=label_list)
        self.examples = self._read_file(self.data_file, is_file_with_header)

        self.records = self._convert_examples_to_records(self.examples)

    def _read_file(self, input_file, is_file_with_header: bool = False) -> List[InputExample]:
        """
        Reads a tab separated value file.
        Args:
            input_file (:obj:str) : The file to be read.
            is_file_with_header(:obj:bool, `optional`, default to :obj: False) :
                Whether or not the file is with the header introduction.
        Returns:
            examples (:obj:`List[InputExample]`): All the input data.
        """
        if not os.path.exists(input_file):
            raise RuntimeError("The file {} is not found.".format(input_file))
        else:
            with io.open(input_file, "r", encoding="UTF-8") as f:
                reader = csv.reader(f, delimiter="\t", quotechar=None)
                examples = []
                seq_id = 0
                header = next(reader) if is_file_with_header else None
                for line in reader:
                    example = InputExample(guid=seq_id, label=line[0], text_a=line[1])
                    seq_id += 1
                    examples.append(example)
                return examples

    def _convert_examples_to_records(self, examples: List[InputExample]) -> List[dict]:
        """
        Converts all examples to records which the model needs.
        Args:
            examples(obj:`List[InputExample]`): All data examples returned by _read_file.
        Returns:
            records(:obj:`List[dict]`): All records which the model needs.
        """
        records = []
        for example in examples:
            record = self.tokenizer.encode(text=example.text_a, text_pair=example.text_b, max_seq_len=self.max_seq_len)
            # CustomTokenizer will tokenize the text firstly and then lookup words in the vocab
            # When all words are not found in the vocab, the text will be dropped.
            if not record:
                logger.info(
                    "The text %s has been dropped as it has no words in the vocab after tokenization." % example.text_a)
                continue
            if example.label:
                record['label'] = self.label_map[example.label]
            records.append(record)
        return records

    def __getitem__(self, idx):
        record = self.records[idx]
        if 'label' in record.keys():
            if isinstance(self.tokenizer, BertTokenizer):
                return np.array(record['input_ids']), np.array(record['segment_ids']), np.array(record['label'])
            elif isinstance(self.tokenizer, CustomTokenizer):
                return np.array(record['text']), np.array(record['seq_len']), np.array(record['label'])
        else:
            if isinstance(self.tokenizer, BertTokenizer):
                return np.array(record['input_ids']), np.array(record['segment_ids'])
            elif isinstance(self.tokenizer, CustomTokenizer):
                return np.array(record['text']), np.array(record['seq_len'])

    def __len__(self):
        return len(self.records)


class SeqLabelingDataset(BaseNLPDataset, paddle.io.Dataset):
    def __init__(self,
                 base_path: str,
                 tokenizer: Union[BertTokenizer, CustomTokenizer],
                 max_seq_len: int = 128,
                 mode: str = "train",
                 data_file: str = None,
                 label_file: str = None,
                 label_list: list = None,
                 split_char="\002",
                 no_entity_label="O",
                 is_file_with_header: bool = False):
        super(SeqLabelingDataset, self).__init__(
            base_path=base_path,
            tokenizer=tokenizer,
            max_seq_len=max_seq_len,
            mode=mode,
            data_file=data_file,
            label_file=label_file,
            label_list=label_list)

        self.no_entity_label = no_entity_label
        self.split_char = split_char

        self.examples = self._read_file(self.data_file, is_file_with_header)
        self.records = self._convert_examples_to_records(self.examples)

    def _read_file(self, input_file, is_file_with_header: bool = False) -> List[InputExample]:
        """Reads a tab separated value file."""
        if not os.path.exists(input_file):
            raise RuntimeError("The file {} is not found.".format(input_file))
        else:
            with io.open(input_file, "r", encoding="UTF-8") as f:
                reader = csv.reader(f, delimiter="\t", quotechar=None)
                examples = []
                seq_id = 0
                header = next(reader) if is_file_with_header else None
                for line in reader:
                    example = InputExample(guid=seq_id, label=line[1], text_a=line[0])
                    seq_id += 1
                    examples.append(example)
                return examples

    def _convert_examples_to_records(self, examples: List[InputExample]) -> List[dict]:
        """
        Returns a list[dict] including all the input information what the model need.
        Args:
            examples (list): the data examples, returned by _read_file.
        Returns:
            a list with all the examples record.
        """
        records = []
        for example in examples:
            tokens, labels = self._reseg_token_label(
                tokens=example.text_a.split(self.split_char),
                labels=example.label.split(self.split_char))
            record = self.tokenizer.encode(
                text=tokens, max_seq_len=self.max_seq_len)
            # CustomTokenizer will tokenize the text firstly and then lookup words in the vocab
            # When all words are not found in the vocab, the text will be dropped.
            if not record:
                logger.info(
                    "The text %s has been dropped as it has no words in the vocab after tokenization."
                    % example.text_a)
                continue
            if labels:
                record["label"] = []
                tokens_with_specical_token = self.tokenizer.decode(
                    record, only_convert_to_tokens=True)
                tokens_index = 0
                for token in tokens_with_specical_token:
                    if tokens_index < len(
                            tokens) and token == tokens[tokens_index]:
                        record["label"].append(
                            self.label_list.index(labels[tokens_index]))
                        tokens_index += 1
                    else:
                        record["label"].append(
                            self.label_list.index(self.no_entity_label))
            records.append(record)
        return records

    def _reseg_token_label(
            self, tokens: List[str], labels: List[str] = None) -> Tuple[List[str], List[str]] or List[str]:
        if labels:
            if len(tokens) != len(labels):
                raise ValueError(
                    "The length of tokens must be same with labels")
            ret_tokens = []
            ret_labels = []
            for token, label in zip(tokens, labels):
                sub_token = self.tokenizer.tokenize(token)
                if len(sub_token) == 0:
                    continue
                ret_tokens.extend(sub_token)
                ret_labels.append(label)
                if len(sub_token) < 2:
                    continue
                sub_label = label
                if label.startswith("B-"):
                    sub_label = "I-" + label[2:]
                ret_labels.extend([sub_label] * (len(sub_token) - 1))

            if len(ret_tokens) != len(ret_labels):
                raise ValueError(
                    "The length of ret_tokens can't match with labels")
            return ret_tokens, ret_labels
        else:
            ret_tokens = []
            for token in tokens:
                sub_token = self.tokenizer.tokenize(token)
                if len(sub_token) == 0:
                    continue
                ret_tokens.extend(sub_token)
                if len(sub_token) < 2:
                    continue
            return ret_tokens, None

    def __getitem__(self, idx):
        record = self.records[idx]
        if 'label' in record.keys():
            if isinstance(self.tokenizer, BertTokenizer):
                return np.array(record['input_ids']), np.array(record['segment_ids']), np.array(record['label'])
            else:  # TODO(chenxiaojie): add CustomTokenizer supported
                raise NotImplementedError
        else:
            if isinstance(self.tokenizer, BertTokenizer):
                return np.array(record['input_ids']), np.array(record['segment_ids'])
            else:  # TODO(chenxiaojie): add CustomTokenizer supported
                raise NotImplementedError

    def __len__(self):
        return len(self.records)
