"""
Logistics Packaging Defect Dataset Generator & PyTorch Dataset.
Synthesizes high-speed conveyor camera inspection frames with surface texture and localized defects.
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np


class SyntheticPackageInspectionDataset(Dataset):
    def __init__(self, n_samples: int = 500, img_size: int = 64, seed: int = 42):
        self.n_samples = n_samples
        self.img_size = img_size
        self.seed = seed
        self.data, self.labels = self._generate_dataset()

    def _generate_dataset(self):
        rng = np.random.default_rng(self.seed)
        images = []
        labels = []

        for _ in range(self.n_samples):
            # Base cardboard / metallic container surface texture
            base = rng.normal(loc=0.55, scale=0.08, size=(3, self.img_size, self.img_size))

            # 50% normal, 50% defective
            is_defect = rng.uniform() > 0.5
            if is_defect:
                # Inject puncture/slash defect (high-contrast dark scratch or bright tear)
                x1, y1 = rng.integers(10, self.img_size - 10, size=2)
                length = rng.integers(15, 30)
                angle = rng.uniform(0, np.pi)
                dx, dy = int(length * np.cos(angle)), int(length * np.sin(angle))
                x2 = np.clip(x1 + dx, 0, self.img_size - 1)
                y2 = np.clip(y1 + dy, 0, self.img_size - 1)

                # Draw defect line
                rr, cc = np.linspace(x1, x2, num=length), np.linspace(y1, y2, num=length)
                for r, c in zip(rr.astype(int), cc.astype(int)):
                    base[:, max(0, r - 1):min(self.img_size, r + 2), max(0, c - 1):min(self.img_size, c + 2)] = 0.05
                labels.append(1)
            else:
                labels.append(0)

            # Clip to valid [0, 1] range
            base = np.clip(base, 0.0, 1.0)
            images.append(base)

        data_tensor = torch.tensor(np.array(images), dtype=torch.float32)
        label_tensor = torch.tensor(labels, dtype=torch.long)
        return data_tensor, label_tensor

    def __len__(self) -> int:
        return self.n_samples

    def __getitem__(self, idx: int):
        return self.data[idx], self.labels[idx]


def get_data_loaders(batch_size: int = 32, train_samples: int = 400, val_samples: int = 100):
    train_ds = SyntheticPackageInspectionDataset(n_samples=train_samples, seed=101)
    val_ds = SyntheticPackageInspectionDataset(n_samples=val_samples, seed=202)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader
