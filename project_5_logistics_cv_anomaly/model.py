"""
PyTorch Deep Convolutional Neural Network for Edge Packaging Defect Inspection.
Includes gradient saliency attribution for explainable vision inspection.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class DefectInspectionCNN(nn.Module):
    def __init__(self, num_classes: int = 2):
        super().__init__()
        # Conv Block 1: 3 -> 16
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(16)

        # Conv Block 2: 16 -> 32
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(32)

        # Conv Block 3: 32 -> 64
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, padding=1, bias=False)
        self.bn3 = nn.BatchNorm2d(64)

        self.pool = nn.MaxPool2d(2, 2)
        self.gap = nn.AdaptiveAvgPool2d((2, 2))

        self.fc1 = nn.Linear(64 * 2 * 2, 64)
        self.dropout = nn.Dropout(p=0.25)
        self.classifier = nn.Linear(64, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Block 1
        x = self.pool(F.leaky_relu(self.bn1(self.conv1(x)), negative_slope=0.1))
        # Block 2
        x = self.pool(F.leaky_relu(self.bn2(self.conv2(x)), negative_slope=0.1))
        # Block 3
        x = self.pool(F.leaky_relu(self.bn3(self.conv3(x)), negative_slope=0.1))

        x = self.gap(x)
        x = torch.flatten(x, 1)
        x = F.leaky_relu(self.fc1(x), negative_slope=0.1)
        x = self.dropout(x)
        logits = self.classifier(x)
        return logits

    def compute_saliency_map(self, input_tensor: torch.Tensor, target_class: int = 1) -> torch.Tensor:
        """
        Computes gradient saliency map attributing defect classification to pixel regions.
        Automatically handles device synchronization.
        """
        self.eval()
        device = next(self.parameters()).device
        x = input_tensor.clone().detach().to(device).requires_grad_(True)
        logits = self.forward(x)
        score = logits[:, target_class].sum()
        score.backward()

        # Maximum gradient across color channels, transferred back to CPU
        saliency, _ = torch.max(x.grad.data.abs(), dim=1)
        return saliency.cpu()
