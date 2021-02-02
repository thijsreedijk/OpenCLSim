# Research using OpenCLSim

This folder contains the code used for research. Read the descriptions below for background information.

## Understanding Uncertainties in Offshore Engineering - Thijs Reedijk (2021)

A study assessing the workability of marine operations. The study focussed at improving project estimates by considering system response of vessels and equipment to wave motion in a discrete-event simulation model (hence, OpenCLSim), rather than using conventional approaches such as wave scattter diagrams.

The study included setting up multiple models in order to prove its effectiveness. The first model is the `BaseModel`, a model in which the installation operation of any abritary offshore wind farm is modelled using deterministic properties and where activities are independent of weather constraints.

The second model is refered to as the `ReferenceModel`, a model in which the activities are effectively constraint to environmental conditions, in particular, the wave height and peak wave period.
