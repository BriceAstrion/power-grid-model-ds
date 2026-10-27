# PGM-DS Visualiser Experiments

## Purpose

This folder contains experiments conducted during the graduation project on extending the PowerGridModel-DS (PGM-DS) visualiser for state-estimation diagnostics.

The experiments investigate how measurement and estimation data can be retrieved, matched, processed, and visualised using the existing PGM-DS architecture.

The results support technical decisions documented in the Project Research, Functional Design, and Software Design documents.

## Experiments

| Experiment | Focus |
| ---------- | ----- |
| PoC-01 | Investigating the identification and matching of electrical components and measurement data |
| PoC-02 | Investigating scenario-data extraction and alignment |
| PoC-03 | Investigating measured-versus-estimated comparison and sigma-based bands |
| PoC-04 | Investigating the integration of voltage visualisation into the existing Dash visualiser |

The experiments are research implementations and should not be considered production-ready functionality.

## Running the Experiments

Each experiment should be run using the instructions and dependencies provided in its own directory, where applicable.

The experiments use the PGM-DS codebase and its existing data structures. Some experiments may require specific workshop datasets or configurations.

Before running an experiment:

1. Set up the PGM-DS development environment according to the repository instructions.
2. Check the experiment's required input datasets and dependencies.
3. Run the experiment using its documented entry point.
4. Compare the results with the expected behaviour described in its experiment documentation.

## Implementation Notes

The experiments are kept separate from the final implementation to distinguish technical investigations from functionality intended for integration into the visualiser.

Where possible, experiments use synthetic or publicly shareable data. Internal datasets, credentials, interview material, and other confidential project information must not be committed.

## Related Documentation

Detailed objectives, test cases, observations, limitations, and conclusions are maintained in the graduation project's research documentation.

The Software Design describes how the findings inform the proposed architecture of the PGM-DS visualiser.
