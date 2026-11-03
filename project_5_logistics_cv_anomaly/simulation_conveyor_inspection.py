"""
End-to-End Conveyor Camera Inspection Simulation.
Simulates high-speed package defect detection, latency timing, and pneumatic rejection divert.
"""

import time
import torch
from dataset import get_data_loaders, SyntheticPackageInspectionDataset
from model import DefectInspectionCNN
from trainer import DefectTrainer, DefectEvaluator


def main():
    print("==========================================================================")
    print("PROJECT 5: SIMULATION / DRY RUN (FLEETVISION REAL-TIME CV INSPECTOR)")
    print("==========================================================================\n")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Phase 1] Initializing PyTorch CNN Pipeline on Hardware Device: [{device.upper()}]...")

    train_loader, val_loader = get_data_loaders(batch_size=32, train_samples=400, val_samples=100)
    model = DefectInspectionCNN(num_classes=2)
    trainer = DefectTrainer(model, device=device, lr=2e-3)

    print("  -> Training model for 3 quick convergence epochs on packaging dataset...")
    for epoch in range(1, 4):
        loss = trainer.train_epoch(train_loader)
        print(f"     Epoch {epoch}/3 - Cross-Entropy Loss: {loss:.4f}")

    print("\n[Phase 2] Evaluating Model on Validation Batch (100 parcels)...")
    eval_metrics = DefectEvaluator.evaluate(model, val_loader, device=device)
    print(f"  * Accuracy:        {eval_metrics['accuracy']:.2%}")
    print(f"  * Defect Recall:   {eval_metrics['recall']:.2%}")
    print(f"  * Precision:       {eval_metrics['precision']:.2%}")
    print(f"  * F1 Score:        {eval_metrics['f1_score']:.4f}")
    print(f"  * Frame Latency:   {eval_metrics['avg_latency_ms_per_frame']} ms/frame")
    print(f"  * Edge Throughput: {eval_metrics['throughput_fps']} FPS")

    print("\n[Phase 3] Simulating High-Speed Conveyor Stream (5 Live Parcels)...")
    stream_ds = SyntheticPackageInspectionDataset(n_samples=5, img_size=64, seed=777)

    for i in range(len(stream_ds)):
        img, ground_truth = stream_ds[i]
        input_tensor = img.unsqueeze(0).to(device)

        t_start = time.perf_counter()
        with torch.no_grad():
            logits = model(input_tensor)
            probs = torch.softmax(logits, dim=1)[0]
            pred_class = torch.argmax(probs).item()
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        is_defective = pred_class == 1
        status = "DEFECT DETECTED" if is_defective else "CLEAN / PASSED"
        action = "[PNEUMATIC REJECT DIVERTER FIRED]" if is_defective else "[CONTINUE DOWNSTREAM]"

        print(f"\n  Parcel #{i + 1} Ingested:")
        print(f"    Inference Latency: {t_elapsed_ms:.2f} ms")
        print(f"    Classification:    {status} (Confidence: {probs[pred_class]:.2%})")
        print(f"    Conveyor Action:   {action}")

        if is_defective:
            # Compute gradient saliency localization
            saliency = model.compute_saliency_map(input_tensor, target_class=1)[0]
            max_r, max_c = torch.where(saliency == saliency.max())
            center_x, center_y = max_c[0].item(), max_r[0].item()
            print(f"    Saliency Localization: Defect centroid at pixel ({center_x}, {center_y})")

    print("\n==========================================================================")
    print("FLEETVISION INSPECTION DRY RUN COMPLETED WITH 0 ERRORS.")
    print("==========================================================================")


if __name__ == "__main__":
    main()
