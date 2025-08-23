Parameter sweep example

Description

Generates several variant PLECS files with different parameter sets and saves them under `examples_output/`.

Usage

python examples/parameter_sweep.py

Notes

- If `pyplecs.generate_variant_plecs_file` is not available this example prints the variants instead of writing files.
- Expects `data/simple_buck.plecs` in the repository for full behavior.
