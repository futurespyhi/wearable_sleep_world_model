"""Test forecast inputs, recurrence, and independent target masks."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from stage_forecast.baselines import fit_persistence, predict_persistence, stage_prior
from stage_forecast.data import fit_standardizer

try:
    import torch
except ImportError:
    torch = None

if torch is not None:
    from stage_forecast.models import ARMS, SleepForecaster, fit_model, masked_losses, predict


class BaselineTests(unittest.TestCase):
    def test_prior_uses_lead_frequency_and_masks_unknown(self):
        stage = np.full((3, 60), -1)
        stage[:, 0] = [0, 1, 1]
        stage[:, 2] = [2, 2, -1]
        prediction = stage_prior(stage, 2)
        np.testing.assert_allclose(prediction[0, 0], [1 / 3, 2 / 3, 0, 0])
        np.testing.assert_allclose(prediction[0, 2], [0, 0, 1, 0])
        np.testing.assert_allclose(prediction[0, 1], [1 / 5, 2 / 5, 2 / 5, 0])
        np.testing.assert_array_equal(prediction[0], prediction[1])

    def test_classifier_learns_current_stage_and_repeats_distribution(self):
        hr = np.zeros((5, 60, 5))
        acc = np.zeros((5, 60, 4))
        hr[:, -1, 0] = [-2, -1, 1, 2, -100]
        classifier = fit_persistence(hr, acc, np.array([0, 0, 3, 3, -1]))
        prediction = predict_persistence(classifier, hr[:4], acc[:4])
        np.testing.assert_array_equal(prediction.argmax(axis=-1), np.repeat([[0], [0], [3], [3]], 60, axis=1))
        np.testing.assert_allclose(prediction.sum(axis=-1), 1)
        np.testing.assert_array_equal(prediction, np.repeat(prediction[:, :1, :], 60, axis=1))
        self.assertEqual(classifier.metadata["current_stage_support"], [2, 0, 0, 2])


@unittest.skipIf(torch is None, "PyTorch is unavailable")
class ForecastTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.hr = torch.randn(3, 60, 5)
        self.acc = torch.randn(3, 60, 4)

    def test_explicit_action_enters_only_the_first_transition_and_states_are_reused(self):
        model = SleepForecaster("explicit", 5, 4)
        before = []
        after = []
        original_advance = model._advance

        def record_advance(state, context, action, lead):
            before.append((state.clone(), context.clone(), action.clone(), lead))
            result = original_advance(state, context, action, lead)
            after.append(result.clone())
            return result

        model._advance = record_advance
        with torch.inference_mode():
            logits, predicted_hr = model(self.hr, self.acc)
            observed_action = model.action_encoder(self.acc[:, -1, :])
            unknown = model.future_unknown.expand(self.hr.shape[0], -1)
            torch.testing.assert_close(before[0][2], observed_action)
            self.assertFalse(torch.equal(observed_action, unknown))
            self.assertEqual([entry[3] for entry in before], list(range(1, 61)))
            for step in range(1, 60):
                torch.testing.assert_close(before[step][0], after[step - 1])
                torch.testing.assert_close(before[step][1], before[0][1])
                torch.testing.assert_close(before[step][2], unknown)
            expected_states = torch.stack(after, dim=1)
            torch.testing.assert_close(logits, model.stage_head(expected_states))
            torch.testing.assert_close(predicted_hr, model.hr_head(expected_states).squeeze(-1))

    def test_explicit_and_fusion_put_the_latest_action_in_different_ports(self):
        changed_acc = self.acc.clone()
        changed_acc[:, -1, :].add_(3)
        for arm in ("explicit", "fusion"):
            with self.subTest(arm=arm):
                model = SleepForecaster(arm, 5, 4)
                first_inputs = []
                original_advance = model._advance

                def record_first(state, context, action, lead):
                    if lead == 1:
                        first_inputs.append((state, context, action))
                    return original_advance(state, context, action, lead)

                model._advance = record_first
                with torch.inference_mode():
                    model(self.hr, self.acc)
                    model(self.hr, changed_acc)
                (state1, context1, action1), (state2, context2, action2) = first_inputs
                torch.testing.assert_close(context1, context2, rtol=0, atol=0)
                self.assertEqual(torch.equal(state1, state2), arm == "explicit")
                self.assertEqual(torch.equal(action1, action2), arm == "fusion")

    def test_hr_only_is_invariant_to_all_acc_inputs(self):
        model = SleepForecaster("hr_only", 5, 4)
        original = predict(model, self.hr.numpy(), self.acc.numpy())
        changed = predict(model, self.hr.numpy(), np.full_like(self.acc.numpy(), np.nan))
        for expected, observed in zip(original, changed):
            np.testing.assert_array_equal(observed, expected)

    def test_stage_and_hr_losses_have_separate_masks_and_normalizers(self):
        logits = torch.zeros(1, 3, 4, requires_grad=True)
        target = torch.tensor([[1, -1, -1]])
        hr_prediction = torch.tensor([[0.0, 1.0, 2.0]], requires_grad=True)
        hr_target = torch.tensor([[float("nan"), 1.5, 5.0]])
        hr_mask = torch.tensor([[False, True, True]])
        stage_loss, hr_loss = masked_losses(logits, target, hr_prediction, hr_target, hr_mask)
        self.assertAlmostEqual(float(stage_loss), np.log(4), places=6)
        self.assertAlmostEqual(float(hr_loss), (0.125 + 2.5) / 2, places=6)
        (stage_loss + 0.1 * hr_loss).backward()
        torch.testing.assert_close(logits.grad[0, 1:], torch.zeros(2, 4))
        torch.testing.assert_close(hr_prediction.grad[0, 0], torch.tensor(0.0))
        self.assertIsNone(masked_losses(logits, torch.full_like(target, -1), hr_prediction, hr_target, hr_mask)[0])
        self.assertIsNone(masked_losses(logits, target, hr_prediction, hr_target, torch.zeros_like(hr_mask))[1])

    def test_each_arm_completes_an_optimizer_step_and_predicts_60_epochs(self):
        hr = self.hr.numpy()
        acc = self.acc.numpy()
        stages = np.tile(np.arange(60) % 5 - 1, (len(hr), 1))
        target_hr = np.zeros_like(stages, dtype=np.float32)
        valid_hr = stages != -1
        target_hr[~valid_hr] = np.nan
        parameters = {}
        for arm in ARMS:
            with self.subTest(arm=arm):
                model, meta = fit_model(arm, hr, acc, stages, target_hr, valid_hr, seed=0, epochs=1)
                probabilities, estimates = predict(model, hr, acc)
                self.assertEqual(probabilities.shape, (len(hr), 60, 4))
                self.assertEqual(estimates.shape, (len(hr), 60))
                np.testing.assert_allclose(probabilities.sum(axis=-1), 1, atol=1e-6)
                self.assertTrue(np.isfinite(estimates).all())
                self.assertEqual(meta["training_history"][0]["optimizer_steps"], 1)
                self.assertEqual(meta["training_history"][0]["hr_targets"], int(valid_hr.sum()))
                parameters[arm] = meta["parameters"]
        self.assertEqual(parameters["hr_only"], parameters["fusion"])
        self.assertEqual(parameters["fusion"], parameters["explicit"])

    def test_mutating_raw_data_at_and_after_cutoff_preserves_every_forecast(self):
        from test_stage_data import cutoff_mutation_histories

        with TemporaryDirectory() as temporary:
            before, after = cutoff_mutation_histories(Path(temporary))
        np.testing.assert_array_equal(before.origin, after.origin)
        np.testing.assert_array_equal(before.origin_time, after.origin_time)
        np.testing.assert_array_equal(before.history, after.history)
        self.assertFalse(np.array_equal(before.stage, after.stage))
        self.assertFalse(np.array_equal(before.future_hr, after.future_hr, equal_nan=True))
        scale = fit_standardizer(before)
        inputs_before = scale.transform(before.history)
        inputs_after = scale.transform(after.history)

        hr = self.hr.numpy()
        acc = self.acc.numpy()
        stage = np.tile(np.arange(60) % 4, (len(hr), 1))
        target_hr = np.zeros_like(stage, dtype=np.float32)
        hr_mask = np.ones_like(stage, dtype=bool)
        np.testing.assert_array_equal(stage_prior(stage, len(before.stage)), stage_prior(stage, len(after.stage)))
        persistence = fit_persistence(hr, acc, np.array([0, 1, 3]))
        np.testing.assert_array_equal(
            predict_persistence(persistence, *inputs_before),
            predict_persistence(persistence, *inputs_after),
        )
        for arm in ARMS:
            with self.subTest(arm=arm):
                model, _ = fit_model(arm, hr, acc, stage, target_hr, hr_mask, seed=0, epochs=1)
                expected = predict(model, *inputs_before)
                observed = predict(model, *inputs_after)
                for before_output, after_output in zip(expected, observed):
                    np.testing.assert_array_equal(after_output, before_output)


if __name__ == "__main__":
    unittest.main()
