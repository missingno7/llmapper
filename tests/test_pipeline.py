"""The compiler owns the pipeline: an emitter that omits a pass is refused.

The fail-first is slice 2h's own defect, made impossible. That emitter never
called `frame_map`, and what reported it was the frames GATE, at 191
misaligned walls -- a number that says nothing about the cause. A gate
downstream of a missing pass can only ever report the symptom.
"""

from __future__ import annotations

import unittest

from bloodmap.channels import Compilation, OrderError
from bloodmap.light_field import Mass
from bloodmap.pipeline import (
    Emission, FrameSpec, JoinSpec, LightSpec, PipelineError, SurfaceSpec,
    compile_city)
from bloodmap import joins

GRADE = 8192
ROAD_Z = GRADE + 2048
SKY = 3491


def _plane():
    """A ring road round one block: a plane with a hole, and its island."""
    return SurfaceSpec(
        surface_id="plane",
        rings=([(0, 0), (24576, 0), (24576, 24576), (0, 24576)],
               [(4096, 4096), (4096, 20480), (20480, 20480), (20480, 4096)]),
        floor_z=ROAD_Z, ceiling_z=ROAD_Z - 6 * 32768,
        floor_tile=352, ceiling_tile=SKY, wall_tile=6, kind=joins.ROAD)


def _island():
    return SurfaceSpec(
        surface_id="island",
        rings=([(4096, 4096), (20480, 4096), (20480, 20480), (4096, 20480)],),
        floor_z=GRADE, ceiling_z=GRADE - 6 * 32768,
        floor_tile=4, ceiling_tile=SKY, wall_tile=4, kind=joins.PAVEMENT)


def _emission(**overrides):
    base = dict(
        name="pipeline-fixture",
        surfaces=[_plane(), _island()],
        declarations=[],
        light=LightSpec(masses=(Mass("mass:block",
                                     ((6144, 6144), (18432, 6144),
                                      (18432, 18432), (6144, 18432)),
                                     4 * 16960),),
                        bearing_units=478, base_shade=8, step=12),
        joins=JoinSpec(strict=False),
        frames=FrameSpec(),
        start=("plane", 0))
    base.update(overrides)
    return Emission(**base)


class TheCompilerOwnsThePipeline(unittest.TestCase):

    def test_an_emitter_that_omits_frames_is_refused_by_the_compiler(self):
        # THE FAIL-FIRST. Slice 2h shipped exactly this and what caught it was
        # the frames gate, at 191 walls -- a symptom, not a cause.
        with self.assertRaises(PipelineError) as caught:
            compile_city(_emission(frames=None))
        self.assertIn("frames", str(caught.exception))
        # and it says nothing about walls, because the cause is not a wall
        self.assertNotIn("191", str(caught.exception))

    def test_each_of_the_five_is_named_when_it_is_the_one_omitted(self):
        for pass_name, attribute in (("planes", "surfaces"),
                                     ("declare", "declarations"),
                                     ("light", "light"),
                                     ("joins", "joins"),
                                     ("frames", "frames")):
            with self.subTest(pass_name):
                with self.assertRaises(PipelineError) as caught:
                    compile_city(_emission(**{attribute: None}))
                self.assertIn(repr(pass_name), str(caught.exception))

    def test_the_refusal_names_the_first_omission_not_the_last(self):
        with self.assertRaises(PipelineError) as caught:
            compile_city(_emission(light=None, frames=None))
        self.assertIn("'light'", str(caught.exception))

    def test_an_empty_declaration_is_a_statement_and_is_not_an_omission(self):
        # "this map has no mechanisms" is a claim; silence is a bug.
        built = compile_city(_emission(declarations=[]))
        self.assertEqual(built.report["declarations"], 0)
        self.assertTrue(built.run.complete)

    def test_the_emitter_never_calls_a_pass(self):
        # The emission is data. Nothing in it is callable, so an emitter has
        # nothing it COULD run out of order.
        emission = _emission()
        for attribute in ("surfaces", "declarations", "light", "joins",
                          "frames"):
            self.assertFalse(callable(getattr(emission, attribute)))

    def test_the_five_passes_ran_in_order(self):
        built = compile_city(_emission())
        self.assertEqual(built.run.done,
                         ["planes", "declare", "light", "joins", "frames"])

    def test_the_fixture_builds_a_map_with_a_kerb_and_a_shadow(self):
        built = compile_city(_emission())
        self.assertGreater(built.report["sectors"], 2)
        self.assertEqual(built.report["partition_faults"], [])
        self.assertEqual(built.report["joins"]["unknown"], [])
        self.assertGreater(built.report["joins"]["written"], 0)
        self.assertIn(1, built.report["levels"])


class CompletenessIsAsserted(unittest.TestCase):

    def test_a_run_that_stops_early_names_the_pass_it_never_entered(self):
        run = Compilation()
        run.enter("planes")
        run.enter("declare")
        run.enter("light")
        with self.assertRaises(OrderError) as caught:
            run.require_complete()
        self.assertIn("'joins'", str(caught.exception))

    def test_a_complete_run_says_nothing(self):
        run = Compilation()
        for name in ("planes", "declare", "light", "joins", "frames"):
            run.enter(name)
        self.assertIsNone(run.require_complete())


if __name__ == "__main__":
    unittest.main()
