"""Past-only sleep-stage models and the fixed first-round training loop."""

from __future__ import annotations

import os
import resource
from time import perf_counter

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F


ARMS = ("direct", "hr_only", "fusion", "explicit")
HISTORY = HORIZON = 60
N_STAGES = 4
STATE_SIZE = 32
ACTION_SIZE = 16
BATCH_SIZE = 64
LEARNING_RATE = 1e-3
TRAIN_EPOCHS = 15
HR_LOSS_WEIGHT = 0.1


class SleepForecaster(nn.Module):
    """A shared history encoder with either direct heads or a recurrent transition."""

    def __init__(self, arm: str, hr_features: int, acc_features: int):
        super().__init__()
        if arm not in ARMS:
            raise ValueError(f"Unrecognized forecast arm {arm!r}")
        self.arm = arm
        self.hr_encoder = nn.GRU(hr_features, STATE_SIZE, batch_first=True)
        self.action_encoder = nn.Sequential(nn.Linear(acc_features, ACTION_SIZE), nn.Tanh())
        self.context_encoder = nn.GRU(STATE_SIZE + ACTION_SIZE, STATE_SIZE, batch_first=True)
        self.empty_action = nn.Parameter(torch.zeros(ACTION_SIZE))
        self.initializer = nn.Linear(STATE_SIZE + ACTION_SIZE, STATE_SIZE)

        if arm == "direct":
            self.stage_head = nn.Linear(2 * STATE_SIZE, HORIZON * N_STAGES)
            self.hr_head = nn.Linear(2 * STATE_SIZE, HORIZON)
        else:
            self.future_unknown = nn.Parameter(torch.empty(ACTION_SIZE))
            nn.init.normal_(self.future_unknown, std=0.02)
            self.transition = nn.Linear(2 * STATE_SIZE + ACTION_SIZE + 1, 2 * STATE_SIZE)
            self.stage_head = nn.Linear(STATE_SIZE, N_STAGES)
            self.hr_head = nn.Linear(STATE_SIZE, 1)

    def _advance(self, state, context, action, lead):
        """Advance the predicted state once with a fixed observation context."""
        time = state.new_full((state.shape[0], 1), lead / HORIZON)
        gate, update = self.transition(torch.cat((state, context, action, time), dim=-1)).chunk(2, dim=-1)
        return state + gate.sigmoid() * update.tanh()

    def forward(self, hr, acc):
        """Read only the 60 completed epochs and return logits and scaled HR."""
        if hr.ndim != 3 or acc.ndim != 3 or hr.shape[:2] != acc.shape[:2] or hr.shape[1] != HISTORY:
            raise ValueError("Forecast inputs must have shape [N,60,features] for both sensors")

        hr_states, _ = self.hr_encoder(hr)
        empty = self.empty_action.expand(hr.shape[0], -1)
        if self.arm == "hr_only":
            actions = empty[:, None, :].expand(-1, HISTORY, -1)
        else:
            actions = self.action_encoder(acc)
        context_input = torch.cat((hr_states[:, :-1, :], actions[:, :-1, :]), dim=-1)
        _, final_context = self.context_encoder(context_input)
        context = final_context.squeeze(0)
        last_action = actions[:, -1, :]
        initial_action = last_action if self.arm in ("fusion", "direct") else empty
        state = self.initializer(torch.cat((hr_states[:, -1, :], initial_action), dim=-1)).tanh()

        if self.arm == "direct":
            features = torch.cat((state, context), dim=-1)
            return self.stage_head(features).reshape(-1, HORIZON, N_STAGES), self.hr_head(features)

        unknown = self.future_unknown.expand(hr.shape[0], -1)
        states = []
        for lead in range(1, HORIZON + 1):
            action = last_action if self.arm == "explicit" and lead == 1 else unknown
            state = self._advance(state, context, action, lead)
            states.append(state)
        predicted = torch.stack(states, dim=1)
        return self.stage_head(predicted), self.hr_head(predicted).squeeze(-1)


def masked_losses(logits, stage, predicted_hr, future_hr, hr_mask):
    """Return independently normalized losses, omitting an unsupported target."""
    stage_mask = stage >= 0
    stage_loss = None
    if stage_mask.any():
        stage_loss = F.cross_entropy(logits[stage_mask], stage[stage_mask])
    hr_loss = None
    if hr_mask.any():
        hr_loss = F.huber_loss(predicted_hr[hr_mask], future_hr[hr_mask], delta=1.0)
    return stage_loss, hr_loss


def fit_model(arm, hr, acc, stage, future_hr_scaled, future_hr_mask, *, seed, device="cpu", epochs=TRAIN_EPOCHS):
    """Train a fresh arm on a fixed seed and record completed epoch costs."""
    if epochs < 1:
        raise ValueError("At least one training epoch is required")
    if not len(hr) or hr.shape[:2] != acc.shape[:2] or hr.shape[1] != HISTORY:
        raise ValueError("Training requires nonempty paired 60-epoch HR/ACC histories")
    if any(arr.shape != (len(hr), HORIZON) for arr in (stage, future_hr_scaled, future_hr_mask)):
        raise ValueError("Stage and HR targets and masks must match the training origins and horizon")
    if not np.isin(stage, [-1, 0, 1, 2, 3]).all():
        raise ValueError("Stage targets must be -1 or a supported class index")
    if not np.isfinite(future_hr_scaled[np.asarray(future_hr_mask, dtype=bool)]).all():
        raise ValueError("HR mask marks a nonfinite HR target as valid")

    device = torch.device(device)
    if device.type == "cuda":
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.cuda.reset_peak_memory_stats(device)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed)
    permutation_rng = torch.Generator().manual_seed(seed)
    fit_started = perf_counter()
    model = SleepForecaster(arm, hr.shape[-1], acc.shape[-1]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    train = (
        torch.as_tensor(hr, dtype=torch.float32),
        torch.as_tensor(acc, dtype=torch.float32),
        torch.as_tensor(stage, dtype=torch.long),
        torch.as_tensor(future_hr_scaled, dtype=torch.float32),
        torch.as_tensor(future_hr_mask, dtype=torch.bool),
    )
    history = []
    model.train()
    for epoch in range(1, epochs + 1):
        started = perf_counter()
        stage_count = hr_count = steps = 0
        stage_total = hr_total = 0.0
        for indices in torch.randperm(len(hr), generator=permutation_rng).split(BATCH_SIZE):
            batch_hr, batch_acc, batch_stage, batch_future_hr, batch_mask = (part[indices].to(device) for part in train)
            logits, predicted_hr = model(batch_hr, batch_acc)
            stage_loss, hr_loss = masked_losses(logits, batch_stage, predicted_hr, batch_future_hr, batch_mask)
            losses = []
            if stage_loss is not None:
                n_stage = int((batch_stage >= 0).sum())
                stage_total += float(stage_loss.detach()) * n_stage
                stage_count += n_stage
                losses.append(stage_loss)
            if hr_loss is not None:
                n_hr = int(batch_mask.sum())
                hr_total += float(hr_loss.detach()) * n_hr
                hr_count += n_hr
                losses.append(HR_LOSS_WEIGHT * hr_loss)
            if losses:
                optimizer.zero_grad(set_to_none=True)
                sum(losses).backward()
                optimizer.step()
                steps += 1

        if not steps:
            raise ValueError("No training origin has a valid stage or HR target")
        if not np.isfinite([stage_total, hr_total]).all():
            raise FloatingPointError(f"Nonfinite training objective in epoch {epoch} for {arm}")
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        history.append({
            "epoch": epoch,
            "seconds": perf_counter() - started,
            "optimizer_steps": steps,
            "stage_targets": stage_count,
            "hr_targets": hr_count,
            "stage_cross_entropy": stage_total / stage_count if stage_count else None,
            "hr_huber": hr_total / hr_count if hr_count else None,
        })

    metadata = {
        "arm": arm,
        "seed": seed,
        "device": str(device),
        "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else "CPU",
        "epochs": epochs,
        "parameters": sum(param.numel() for param in model.parameters()),
        "state_size": STATE_SIZE,
        "action_size": ACTION_SIZE,
        "batch_size": BATCH_SIZE,
        "optimizer": "Adam",
        "learning_rate": LEARNING_RATE,
        "hr_loss_weight": HR_LOSS_WEIGHT,
        "epoch_seconds": [entry["seconds"] for entry in history],
        "fit_seconds": perf_counter() - fit_started,
        "peak_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
        "device_peak_allocated_mib": torch.cuda.max_memory_allocated(device) / 2**20 if device.type == "cuda" else None,
        "training_history": history,
    }
    return model, metadata


@torch.inference_mode()
def predict(model, hr, acc, *, device="cpu"):
    """Forecast held-out histories without accepting targets or future sensors."""
    if len(hr) != len(acc):
        raise ValueError("Prediction requires matching HR and ACC origins")
    model = model.to(device)
    model.eval()
    stage, future_hr = [], []
    for start in range(0, len(hr), BATCH_SIZE):
        batch = slice(start, start + BATCH_SIZE)
        logits, prediction_hr = model(
            torch.as_tensor(hr[batch], dtype=torch.float32, device=device),
            torch.as_tensor(acc[batch], dtype=torch.float32, device=device),
        )
        stage.append(logits.softmax(dim=-1).cpu().numpy())
        future_hr.append(prediction_hr.cpu().numpy())
    if not stage:
        return np.empty((0, HORIZON, N_STAGES), np.float32), np.empty((0, HORIZON), np.float32)
    return np.concatenate(stage, axis=0), np.concatenate(future_hr, axis=0)
