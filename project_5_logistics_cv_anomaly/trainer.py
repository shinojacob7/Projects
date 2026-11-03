"""
Training and Evaluation Modules for FleetVision Defect Inspector.
"""

import time
from typing import Dict, Any, Tuple
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from model import DefectInspectionCNN


class DefectTrainer:
    def __init__(self, model: DefectInspectionCNN, device: str = "cpu", lr: float = 1e-3):
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)

    def train_epoch(self, dataloader) -> float:
        self.model.train()
        total_loss = 0.0
        total_samples = 0

        for images, labels in dataloader:
            images, labels = images.to(self.device), labels.to(self.device)
            batch_size = images.size(0)
            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item() * batch_size
            total_samples += batch_size

        return total_loss / max(1, total_samples)


class DefectEvaluator:
    @staticmethod
    def evaluate(model: DefectInspectionCNN, dataloader, device: str = "cpu") -> Dict[str, Any]:
        device = torch.device(device)
        model.eval()
        all_preds = []
        all_labels = []
        latencies = []

        with torch.no_grad():
            for images, labels in dataloader:
                images = images.to(device)
                t0 = time.perf_counter()
                outputs = model(images)
                t1 = time.perf_counter()

                latencies.append((t1 - t0) / images.size(0))
                preds = torch.argmax(outputs, dim=1).cpu().numpy()
                all_preds.extend(preds)
                all_labels.extend(labels.numpy())

        acc = accuracy_score(all_labels, all_preds)
        prec, rec, f1, _ = precision_recall_fscore_support(all_labels, all_preds, average="binary", zero_division=0)
        cm = confusion_matrix(all_labels, all_preds).tolist()
        avg_latency_ms = (sum(latencies) / len(latencies)) * 1000.0 if latencies else 0.0

        return {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "confusion_matrix": cm,
            "avg_latency_ms_per_frame": round(avg_latency_ms, 3),
            "throughput_fps": round(1000.0 / avg_latency_ms, 1) if avg_latency_ms > 0 else 0.0,
        }
