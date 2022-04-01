################################################################################
# Copyright (c) 2021 ContinualAI.                                              #
# Copyrights licensed under the MIT License.                                   #
# See the accompanying LICENSE file for terms.                                 #
#                                                                              #
# Date: 03-31-2022                                                             #
# Author: Zhiqiu Lin                                                           #
# E-mail: zl279@cornell.edu                                                    #
# Website: https://clear-benchmark.github.io                                   #
################################################################################

""" This module contains the high-level CLEAR benchmark/factor generator.
In the original CLEAR benchmark paper (https://arxiv.org/abs/2201.06289),
a novel Streaming evaluation protocol is proposed in contrast to traditional
IID evaluation protocol for CL. The major difference lies in that: 

IID Protocol: Sample a test set from current task, which requires splitting
    the data into 7:3 train:test set.
Streaming Protocol: Use the data of next task as the test set for current task,
    which is arguably more realistic since real-world model training and 
    deployment usually takes considerable amount of time. By the time the 
    model is applied, the task has already drifted.
    
We support both evaluation protocols for benchmark construction."""

from pathlib import Path
from typing import Union, Any, Optional
from typing_extensions import Literal

from avalanche.benchmarks.classic.classic_benchmarks_utils import (
    check_vision_benchmark,
)
from avalanche.benchmarks.datasets.clear import (
    CLEARImage,
    CLEARFeature,
    SEED_LIST,
    CLEAR_FEATURE_TYPES
)
from avalanche.benchmarks.scenarios.generic_benchmark_creation import (
    create_generic_benchmark_from_paths,
    create_generic_benchmark_from_tensor_lists,
)

EVALUATION_PROTOCOLS = ['iid', 'streaming']


def CLEAR(
    *,
    evaluation_protocol: str = "streaming",
    feature_type: str = None,
    seed: int = None,
    train_transform: Optional[Any] = None,
    eval_transform: Optional[Any] = None,
    dataset_root: Union[str, Path] = None
):
    """
    Creates a Domain-Incremental benchmark for CLEAR10 
    with 10 illustrative classes and an 11th background class.

    If the dataset is not present in the computer, **this method will be
    able to automatically download** and store it.

    This generator supports benchmark construction of both 'iid' and 'streaming'
    evaluation_protocol. The main difference is:
    
    'iid': Always sample testset from current task, which requires
        splitting the data into 7:3 train:test with a given random seed.    
    'streaming': Use all data of next task as the testset for current task,
        which does not split the data and does not require random seed.
        

    The generator supports both Image and Feature (Tensor) datasets.
    If feature_type == None, then images will be used.
    If feature_type is specified, then feature tensors will be used.
    
    The benchmark instance returned by this method will have two fields,
    `train_stream` and `test_stream`, which can be iterated to obtain
    training and test :class:`Experience`. Each Experience contains the
    `dataset` and the associated task label.
    
    Note that the train/test streams will still be data of current task,
    regardless of whether evaluation protocol is 'iid' or 'streaming'.
    For 'iid' protocol, train stream is 70% of current task data,
    and test stream is 30% of current task data.
    For 'streaming' protocol, train stream is 100% of current task data,
    and test stream is just a duplicate of train stream.
    
    The task label "0" will be assigned to each experience.

    :param evaluation_protocol: Choose from ['iid', 'streaming']
        if chosen 'iid', then must specify a seed between [0,1,2,3,4];
        if chosen 'streaming', then the seed will be ignored.
    :param feature_type: Whether to return raw RGB images or feature tensors
        extracted by pre-trained models. Can choose between 
        [None, 'moco_b0', 'moco_imagenet', 'byol_imagenet', 'imagenet'].
        If feature_type is None, then images will be returned.
        Otherwise feature tensors will be returned.
    :param seed: If evaluation_protocol is iid, then must specify a seed value
        for train:test split. Choose between [0,1,2,3,4].
    :param train_transform: The transformation to apply to the training data,
        e.g. a random crop, a normalization or a concatenation of different
        transformations (see torchvision.transform documentation for a
        comprehensive list of possible transformations). Defaults to None.
        If returning feature tensors, then train_transform must be None.
    :param eval_transform: The transformation to apply to the test data,
        e.g. a random crop, a normalization or a concatenation of different
        transformations (see torchvision.transform documentation for a
        comprehensive list of possible transformations). Defaults to None.
        If returning feature tensors, then eval_transform must be None.
    :param dataset_root: The root path of the dataset.
        Defaults to None, which means that the default location for
        'clear10' will be used.

    :returns: a properly initialized :class:`GenericCLScenario` instance.
    """
    data_name = 'clear10'
    """
        We will support clear100 by May, 2022
    """

    assert evaluation_protocol in EVALUATION_PROTOCOLS, (
        "Must specify a evaluation protocol from "
        f"{EVALUATION_PROTOCOLS}"
    )
    
    if evaluation_protocol == "streaming":
        assert seed is None, (
            "Seed for train/test split is not required "
            "under streaming protocol"
        )
        train_split = 'all'
        test_split = 'all'
    elif evaluation_protocol == 'iid':
        assert seed in SEED_LIST, "No seed for train/test split"
        train_split = 'train'
        test_split = 'test'
    else:
        raise NotImplementedError()
    
    if feature_type is None:
        assert isinstance(train_transform, type(None)), "No image transform"
        assert isinstance(eval_transform, type(None)), "No image transform"
        clear_dataset_train = CLEARImage(
            root=dataset_root,
            data_name=data_name,
            download=True,
            split=train_split,
            seed=seed,
            transform=train_transform,
        )
        clear_dataset_test = CLEARImage(
            root=dataset_root,
            data_name=data_name,
            download=True,
            split=test_split,
            seed=seed,
            transform=eval_transform,
        )
        train_samples = clear_dataset_train.paths_and_targets
        test_samples = clear_dataset_test.paths_and_targets
        benchmark_generator = create_generic_benchmark_from_paths
    else:
        assert isinstance(train_transform, type(None)), "Feature transform"
        assert isinstance(eval_transform, type(None)), "Feature transform"
        clear_dataset_train = CLEARFeature(
            root=dataset_root,
            data_name=data_name,
            download=True,
            feature_type=feature_type,
            split=train_split,
            seed=seed,
        )
        clear_dataset_test = CLEARFeature(
            root=dataset_root,
            data_name=data_name,
            download=True,
            feature_type=feature_type,
            split=test_split,
            seed=seed,
        )
        train_samples = clear_dataset_train.tensors_and_targets
        test_samples = clear_dataset_test.tensors_and_targets
        benchmark_generator = create_generic_benchmark_from_tensor_lists
    
    benchmark_obj = benchmark_generator(
        train_samples,
        test_samples,
        task_labels=[0 for _ in range(len(train_samples))],
        complete_test_set_only=False,
        train_transform=train_transform,
        eval_transform=eval_transform,
    )
    
    return benchmark_obj


__all__ = ["CLEAR"]

if __name__ == "__main__":
    import sys
    from torchvision import transforms
    import torch

    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
    transform = transforms.Compose([
        transforms.Resize(224),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        normalize,
    ])
    
    data_name = 'clear10'
    root = f"../avalanche_datasets/{data_name}"
    
    for p in EVALUATION_PROTOCOLS:
        seed_list = [None] if p == 'streaming' else SEED_LIST
        for f in CLEAR_FEATURE_TYPES[data_name] + [None]:
            t = transform if f is None else None
            for seed in seed_list:
                benchmark_instance = CLEAR(
                    evaluation_protocol=p,
                    feature_type=f,
                    seed=seed,
                    train_transform=t,
                    eval_transform=t,
                    dataset_root=root
                )
                # check_vision_benchmark(benchmark_instance)
                print(
                    f"Check pass for {p} protocol, and "
                    f"feature type {f} and seed {seed}"
                )
    sys.exit(0)
