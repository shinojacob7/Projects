"""
Unit Test Suite for FleetVision Packaging Defect Vision Pipeline.
"""

import pytest
import torch
from dataset import SyntheticPackageInspectionDataset, get_data_loaders
from model import DefectInspectionCNN
from trainer import DefectTrainer, DefectEvaluator


def test_dataset_generation():
    ds = SyntheticPackageInspectionDataset(n_samples=20, img_size=64, seed=42)
    assert len(ds) == 20
    img, label = ds[0]
    assert img.shape == (3, 64, 64)
    assert label.item() in [0, 1]
    assert torch.all(img >= 0.0)
    assert torch.all(img <= 1.0)


def test_model_forward_pass():
    model = DefectInspectionCNN(num_classes=2)
    dummy_input = torch.randn(4, 3, 64, 64)
    logits = model(dummy_input)
    assert logits.shape == (4, 2)
    # Probs must sum to 1 after softmax
    probs = torch.softmax(logits, dim=1)
    assert torch.allclose(probs.sum(dim=1), torch.ones(4), atol=1e-5)


def test_backward_gradient_flow():
    model = DefectInspectionCNN(num_classes=2)
    trainer = DefectTrainer(model, device="cpu", lr=1e-3)
    dummy_x = torch.randn(8, 3, 64, 64)
    dummy_y = torch.tensor([0, 1, 0, 1, 0, 1, 0, 1], dtype=torch.long)

    # Initial weights
    initial_weight = model.classifier.weight.clone().detach()

    loader = [(dummy_x, dummy_y)]
    loss = trainer.train_epoch(loader)

    assert loss > 0.0
    # Weights should be updated
    assert not torch.equal(initial_weight, model.classifier.weight)


def test_gradient_saliency_attribution():
    model = DefectInspectionCNN(num_classes=2)
    sample_img = torch.randn(2, 3, 64, 64)
    saliency = model.compute_saliency_map(sample_img, target_class=1)

    assert saliency.shape == (2, 64, 64)
    assert torch.all(saliency >= 0.0)
    # Defect areas should have non-zero gradient impact
    assert saliency.sum() > 0.0


def test_evaluator_metrics():
    model = DefectInspectionCNN(num_classes=2)
    train_loader, val_loader = get_data_loaders(batch_size=16, train_samples=32, val_samples=16)
    metrics = DefectEvaluator.evaluate(model, val_loader, device="cpu")

    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1_score" in metrics
    assert "avg_latency_ms_per_frame" in metrics
    assert metrics["avg_latency_ms_per_frame"] > 0.0
