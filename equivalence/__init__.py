"""Functional-equivalence verification for the benchmark implementations.

sim      exact state-vector simulator with deferred terminal measurement and branching
extract  loads each source file through its own SDK (Qiskit circuit data, Cirq operations,
         PennyLane tape, Q# compiled to QIR) and converts it to a common gate-level IR
specs    analytic reference semantics derived from each algorithm's definition
"""
